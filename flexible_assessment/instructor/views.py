import csv
import json
import logging
from datetime import datetime
import dateutil.parser
from io import TextIOWrapper
from threading import Thread
from datetime import datetime

import flexible_assessment.class_views as views
import flexible_assessment.models as models
import flexible_assessment.utils as utils
import pytz

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When
from django.forms import BaseModelFormSet, ValidationError
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect

from instructor.canvas_api import FlexCanvas
from decimal import Decimal, ROUND_HALF_UP
from . import grader, writer
from .forms import (
    AssessmentFileForm,
    AssessmentGroupForm,
    CourseSettingsForm,
    OptionsForm,
    OrderingForm,
    StudentAssessmentBaseForm,
    get_assessment_formset,
)

logger = logging.getLogger(__name__)


def round_half_up(value, digits=2):
    if value is None:
        return None
    """Rounds a float to the specified number of digits using ROUND_HALF_UP"""
    d = Decimal(str(value))  # Convert to Decimal
    return d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)


class InstructorHome(views.InstructorTemplateView):
    template_name = "instructor/instructor_home.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)
        return response


class FlexAssessmentListView(views.ExportView, views.InstructorListView):
    """ListView for student flexible allocations"""

    template_name = "instructor/percentage_list.html"

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        if self.kwargs.get("csv", ""):
            response = writer.students_csv(course, students)

            logger.info(
                "Percentage view exported",
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )
        elif self.kwargs.get("log", ""):
            response = writer.course_log(course)

            logger.info(
                "Course log exported",
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

        return response


class FinalGradeListView(views.ExportView, views.InstructorListView):
    """ListView for student final grades with default and override scores"""

    template_name = "instructor/final_grade_list.html"

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)
        groups = self.get_context_data().get("groups")

        csv_response = writer.grades_csv(course, students, groups)

        logger.info(
            "Final list view exported",
            extra={"course": str(course), "user": self.request.session["display_name"]},
        )

        return csv_response

    def post(self, request, *args, **kwargs):
        """Sets override grades for students on Canvas"""

        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        log_extra = {"course": str(course), "user": request.session["display_name"]}

        if self.kwargs.get("submit", False):
            canvas = FlexCanvas(request)

            canvas.set_override_true(course_id)

            if not canvas.is_allow_override(course_id):
                messages.error(
                    request,
                    "You must enable the 'Final Grade Override'"
                    "in the settings on the Grades page in Canvas.",
                )

                logger.info(
                    "Allow Final Grade Override setting" "not checked in Canvas",
                    extra=log_extra,
                )

                return HttpResponseRedirect(
                    reverse("instructor:final_grades", kwargs={"course_id": course_id})
                )
            success = self._submit_final_grades(course_id, canvas)
            if not success:
                messages.error(
                    request,
                    "Something went wrong when submitting grades!" "Please try again.",
                )

                logger.info("Error in submitting final grades", extra=log_extra)

                return HttpResponseRedirect(
                    reverse("instructor:final_grades", kwargs={"course_id": course_id})
                )

            logger.info("Completed final grades submission to Canvas", extra=log_extra)

        release_total = request.POST.get("release_total") != "on"
        canvas.get_course(course_id).update_settings(hide_final_grades=release_total)

        return HttpResponseRedirect(
            reverse("instructor:instructor_home", kwargs={"course_id": course_id})
        )

    def get_context_data(self, **kwargs):
        """Adds Canvas Assignment Groups to context for rendering grades

        Returns
        -------
        context : context
            Request context
        """

        context = super().get_context_data(**kwargs)
        course_id = self.kwargs["course_id"]
        # Access the session variable to determine which method to call
        flat_grade = self.request.session.get("flat", False) == True
        if flat_grade:
            # If 'flat' is true, call a method that handles flat grades
            groups, _ = FlexCanvas(self.request).get_flat_groups_and_enrollments(
                course_id
            )
        else:
            # If 'flat' is false or not set, call the standard method
            groups, _ = FlexCanvas(self.request).get_groups_and_enrollments(course_id)
        context["groups"] = groups

        context["canvas_domain"] = settings.CANVAS_DOMAIN

        return context

    def _submit_final_grades(self, course_id, canvas):
        """Uploads final override grades in batches to Canvas"""

        def _set_override(student_name, enrollment_id, override, incomplete):
            canvas.set_override(enrollment_id, override, incomplete)
            logger.info(
                "Submitted %s final grade to Canvas",
                student_name,
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

        course = models.Course.objects.get(pk=course_id)
        groups, enrollments = canvas.get_groups_and_enrollments(course_id)

        threads = []
        incomplete = [False]
        batch_size = 64
        for student_id, enrollment_id in enrollments.items():
            student = models.UserProfile.objects.filter(pk=student_id).first()
            if not student:
                continue
            override = grader.get_override_total(
                groups, student, course
            ) or grader.get_default_total(groups, student)

            t = Thread(
                target=_set_override,
                args=(student.display_name, enrollment_id, override, incomplete),
            )
            threads.append(t)

            if len(threads) >= batch_size:
                [t.start() for t in threads]
                [t.join() for t in threads]
                threads = []

        [t.start() for t in threads]
        [t.join() for t in threads]

        return not incomplete[0]


class AssessmentGroupView(views.InstructorFormView):
    """FormView for matching assessments in the app
    to assignment groups on Canvas
    """

    template_name = "instructor/assessment_group_form.html"
    form_class = AssessmentGroupForm
    success_reverse_name = "instructor:final_grades"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["canvas_domain"] = settings.CANVAS_DOMAIN

        return context

    def get_form_kwargs(self):
        """Adds course_id, FlexCanvas instance, and assessments as keyword
        arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super().get_form_kwargs()

        course_id = self.kwargs["course_id"]

        canvas_course = FlexCanvas(self.request).get_course(course_id)

        kwargs["canvas_course"] = canvas_course
        kwargs["assessments"] = models.Assessment.objects.filter(
            course_id=course_id
        ).order_by("order")

        self.kwargs["hide_weights"] = not canvas_course.apply_assignment_group_weights

        return kwargs

    def form_valid(self, form):
        """Validates that each assessment is matched to one Canvas assignment group
        and each Canvas assignment group is matched to zero or one assessments.
        Adds AssignmentGroup from form as Foreign Key to Assessment. Changes
        group weights on Canvas to match default allocations and unmatched
        group weights are set to zero.

        Parameters
        ----------
        form : AssessmentGroupForm
            Matched flexible assessments and Canvas assignment groups

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error in form
        """
        weight_option = form.cleaned_data.pop("weight_option", "default")

        matched_groups = form.cleaned_data.values()

        duplicates = []
        seen = set()
        for group in matched_groups:
            if group in seen:
                duplicates.append(group)
            else:
                seen.add(group)

        items = list(form.cleaned_data.items())
        for field, group in items:
            if group in duplicates:
                form.add_error(field, ValidationError("Matched groups must be unique"))

        if form.errors:
            response = super().form_invalid(form)
            return response

        # Set the session variable to flat if weight_option is equal_weights
        # print(form.cleaned_data)
        self._update_assessments_and_groups(form)
        if weight_option == "equal_weights":
            self.request.session["flat"] = True
        else:
            self.request.session["flat"] = False

        response = super().form_valid(form)
        return response

    def _update_assessments_and_groups(self, form):
        """Adds assignment group to assessment, updates
        Canvas group weights
        """

        course_id = self.kwargs["course_id"]

        canvas_course = FlexCanvas(self.request).get_course(course_id)
        course_name = canvas_course.__getattribute__("name")

        for assessment_id, group_id in form.cleaned_data.items():
            assessment = models.Assessment.objects.get(pk=assessment_id)
            assessment.group = int(group_id)
            assessment.save()

            group = canvas_course.get_assignment_group(group_id)
            group.edit(group_weight=assessment.default)
            group_name = group.__getattribute__("name")

            logger.info(
                "Matched %s to Canvas %s group",
                assessment.title,
                group_name,
                extra={
                    "course": course_name,
                    "user": self.request.session["display_name"],
                },
            )

        matched_group_ids = [int(id) for id in form.cleaned_data.values()]
        canvas_group_ids = [group.id for group in canvas_course.get_assignment_groups()]

        unmatched_group_ids = list(
            filter(lambda id: id not in matched_group_ids, canvas_group_ids)
        )

        for id in unmatched_group_ids:
            canvas_course.get_assignment_group(id).edit(group_weight=0)


class InstructorAssessmentView(views.ExportView, views.InstructorFormView):
    """FormView for instructor setup of flexible assessment for a course"""

    template_name = "instructor/instructor_form.html"
    form_class = BaseModelFormSet
    success_reverse_name = "instructor:instructor_home"

    def get_context_data(self, **kwargs):
        """Populates and adds assessment formset, date form, ordering form, and options
        form to context

        Returns
        -------
        context : context
            Request context
        """
        context = super().get_context_data(**kwargs)
        course = context["course"]

        canvas = FlexCanvas(self.request)
        canvas_course = canvas.get_course(course.id)
        course_settings = canvas_course.get_settings()

        context["is_different"] = False

        # Checks to see if the calendar matches the flex dates
        if course.calendar_id is not None:
            try:
                # If the difference exceeds an hour, the is_different context variable is set to True to launch a modal in the browser
                formatted_calendar_date = dateutil.parser.isoparse(
                    canvas.get_calendar_event(str(course.calendar_id)).end_at
                )
                if (
                    abs(
                        ((course.close - formatted_calendar_date).days) * 60 * 60 * 24
                        + ((course.close - formatted_calendar_date).seconds)
                    )
                    > 3600
                ):
                    context["is_different"] = True
            except:
                pass

        if not course.open:
            hide_total = True
        else:
            hide_total = course_settings["hide_final_grades"]

        context["date_form"] = CourseSettingsForm(
            self.request.POST or None, instance=course, prefix="date"
        )
        context["options_form"] = OptionsForm(
            self.request.POST or None,
            prefix="options",
            hide_total=hide_total,
            hide_weights=not canvas_course.apply_assignment_group_weights,
        )

        context["ordering_form"] = OrderingForm(self.request.POST, prefix="ordering")

        if self.request.POST:
            AssessmentFormSet = get_assessment_formset()
            context["formset"] = AssessmentFormSet(
                self.request.POST, prefix="assessment"
            )

        elif self.request.GET.get("initial", False):
            fields_str = self.request.GET.get("initial", "")
            initial = self._to_initial_dict(fields_str)

            AssessmentFormSet = get_assessment_formset(extra=len(initial))
            context["formset"] = AssessmentFormSet(
                queryset=models.Assessment.objects.none(),
                initial=initial,
                prefix="assessment",
            )
            context["populated"] = True

        else:
            qs = models.Assessment.objects.filter(course=course)
            if len(qs) > 0:
                qs = qs.order_by("order")

            AssessmentFormSet = get_assessment_formset()
            context["formset"] = AssessmentFormSet(queryset=qs, prefix="assessment")

        return context

    def export_list(self):
        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        csv_response = writer.assessments_csv(course)
        return csv_response

    def post(self, request, *args, **kwargs):
        """Defines the assessment formset, date form, and options form
        for validation
        """
        course_id = self.kwargs["course_id"]
        reset_param = request.GET.get("reset")
        if reset_param == "true":
            course = models.Course.objects.get(pk=course_id)
            user = models.UserProfile.objects.get(
                pk=self.request.session["_auth_user_id"]
            )
            old_user_course = models.UserCourse.objects.get(user=user, course=course)

            logger.info(
                "RESETTING COURSE INITIATED BY %s",
                user.display_name,
                extra={
                    "course": course.title,
                    "user": self.request.session["display_name"],
                },
            )

            current_flexes = models.FlexAssessment.objects.filter(
                assessment__course=course.id
            )
            logger.info(
                "FLEXES RESET ARE %s",
                current_flexes,
                extra={
                    "course": course.title,
                    "user": self.request.session["display_name"],
                },
            )

            course_title = course.title
            course.delete()
            new_course = utils.set_course(course_id, course_title)
            utils.set_user_course_enrollment(user, new_course, old_user_course.role)

            return HttpResponseRedirect(
                reverse("instructor:instructor_home", kwargs={"course_id": course_id})
            )

        date_form = CourseSettingsForm(
            request.POST,
            instance=models.Course.objects.get(pk=course_id),
            prefix="date",
        )

        AssessmentFormSet = get_assessment_formset()

        formset = AssessmentFormSet(request.POST, prefix="assessment")
        options_form = OptionsForm(request.POST, prefix="options")
        ordering_form = OrderingForm(request.POST, prefix="ordering")

        if formset.is_valid() and date_form.is_valid() and options_form.is_valid():
            return self.forms_valid(formset, date_form, options_form, ordering_form)

        elif not formset.is_valid():
            return self.form_invalid(formset)
        elif not date_form.is_valid():
            return self.form_invalid(date_form)
        else:
            return self.form_invalid(options_form)

    def forms_valid(self, formset, date_form, options_form, ordering_form):
        """Validates and saves assessment formset and date form and creates
        or removes related flexible assessments, and updates relevant Canvas
        course settings using options form

        Parameters
        ----------
        formset : AssessmentFormSet
            Contains assignment forms and their submitted form data
        date_form : DateForm
            Contains flex assessment open and close datetime
        options_form : OptionsForm
            Contains options for the course setup
        ordering_form: OrderingForm
            Contains the id order of the assessments when rearranged

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if formset and date form is valid,
            TemplateResponse if error
        """

        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        self._set_flex_availability(date_form, course)

        options_form.clean()

        hide_total = options_form.cleaned_data["hide_total"]
        ignore_conflicts = options_form.cleaned_data["ignore_conflicts"]

        assessments, conflict_students = self._save_assessments(
            formset.forms, course, ignore_conflicts
        )

        if conflict_students and not ignore_conflicts:
            # ensures that the order of the forms remains even if they are invalid
            self.save_new_ordering(ordering_form, course, assessments)
            return super().form_invalid(formset)

        assessment_created = self._create_assessments(course, assessments)
        assessment_deleted = self._delete_assessments(course, assessments)
        self.save_new_ordering(ordering_form, course, assessments)

        if assessment_created or assessment_deleted:
            self._reset_all_students(course)
        else:
            self._reset_conflict_students(course, conflict_students)

        # Update Canvas settings
        canvas_course = FlexCanvas(self.request).get_course(course_id)
        canvas_course.update_settings(hide_final_grades=hide_total)
        hide_weights = options_form.cleaned_data["hide_weights"]
        canvas_course.update(
            course={"apply_assignment_group_weights": not hide_weights}
        )

        return HttpResponseRedirect(self.get_success_url())

    def _set_flex_availability(self, date_form, course):
        """
        Sets the time period in which students are able to select the assessment weights
        Updates the log to show date changes
        Creates or updated calendar event in Canvas

        Parameters
        -----------
        date_form: DateForm
            Contains flex assessment open and close datetime
        course: CourseObject
            The database entry for this specific course
        """
        old_dts = tuple(
            map(
                lambda dt: (
                    dt.astimezone(pytz.timezone("America/Vancouver"))
                    if dt is not None
                    else "None"
                ),
                (course.open, course.close),
            )
        )

        date_form.save()

        new_dts = (date_form.cleaned_data["open"], date_form.cleaned_data["close"])
        calendar_created = False
        if course.calendar_id is None:
            event_details = {
                "context_code": ("course_" + str(course.id)),
                "title": ("Flexible Assessment"),
                "start_at": date_form.cleaned_data["close"],
                "end_at": date_form.cleaned_data["close"],
                "all_day": True,
                "description": "If you have not made your choices by this deadline, your choices will be  <strong>automatically set to the default percentages</strong>",
            }
            calendar_event = FlexCanvas(self.request).create_calendar_event(
                event_details
            )
            course.calendar_id = calendar_event.id
            # Updates only the calendar id so it is not NULL on submission as it doesn't have a field in the form
            course.save(update_fields=["calendar_id"])
            calendar_created = True

            logger.info(
                "Created new calendar event " "with id: %s",
                course.calendar_id,
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

        """
        Checks to see if the Calendar event exists in Canvas by attempting to update it
        Calendar events still exist after deletion, only return error after trying to update
        """
        try:
            calendar_event = FlexCanvas(self.request).get_calendar_event(
                course.calendar_id
            )
            calendar_event.edit(calendar_event={"title": ("Flexible Assessment")})
        except:
            event_details = {
                "context_code": ("course_" + str(course.id)),
                "title": ("Flexible Assessment"),
                "start_at": date_form.cleaned_data["close"],
                "end_at": date_form.cleaned_data["close"],
                "all_day": True,
                "description": "If you have not made your choices by this deadline, your choices will be <strong>automatically set to the default percentages</strong>",
            }
            calendar_event = FlexCanvas(self.request).create_calendar_event(
                event_details
            )
            course.calendar_id = calendar_event.id
            course.save(update_fields=["calendar_id"])
            logger.info(
                "Calendar event not found, created new one with id %s and date %s",
                course.calendar_id,
                date_form.cleaned_data["close"],
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

        # Updates both flex dates and calendar if date is changed
        if old_dts != new_dts:
            logger.info(
                "Updated flex availability " "from %s - %s to %s - %s",
                *old_dts,
                *new_dts,
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                }
            )
            calendar_event = FlexCanvas(self.request).get_calendar_event(
                course.calendar_id
            )
            calendar_event_old = calendar_event.end_at
            calendar_event.edit(
                calendar_event={
                    "title": ("Flexible Assessment"),
                    "start_at": date_form.cleaned_data["close"],
                    "end_at": date_form.cleaned_data["close"],
                    "all_day": True,
                    "description": "If you have not made your choices by this deadline, your choices will be  <strong>automatically set to the default percentages</strong>",
                }
            )
            logger.info(
                "Calendar event with id %s updated from %s to %s",
                course.calendar_id,
                calendar_event_old,
                date_form.cleaned_data["close"],
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

    def save_new_ordering(self, ordering_form, course, assessments):
        """
        Ordering form numbers forms in original order
        The new order reflects the position of each form based on their initial index
        e.g. [2, 4, 0, 1, 3] -> the form that initially had index 2 will be at the start
        followed by the one that initially had index 4 etc.

        This function assigns the index of ordered_ids to the order field of the respective assessment
        """
        if ordering_form.is_valid():
            if ordering_form != None:
                ordered_ids = ordering_form.cleaned_data["ordering"].split(",")
                for i in range(len(ordered_ids)):
                    if ordered_ids[i] != "":
                        try:
                            curr = assessments[int(ordered_ids[i])]
                            curr.order = i
                            curr.save()
                        except:
                            return

    def _save_assessments(self, forms, course, ignore_conflicts):
        assessments = []
        conflict_students = set()
        for form in forms:
            assessment = form.save(commit=False)
            assessments.append(assessment)
            assessment.course = course

            curr_conflict_students = assessment.check_valid_flex()
            conflict_students = conflict_students.union(curr_conflict_students)

            if curr_conflict_students and not ignore_conflicts:
                messages.warning(
                    self.request,
                    "{} flex allocations are out of range for {}".format(
                        len(curr_conflict_students), assessment.title
                    ),
                )

        return assessments, conflict_students

    def _create_assessments(self, course, assessments):
        log_extra = {
            "course": str(course),
            "user": self.request.session["display_name"],
        }
        assessment_created = False

        for assessment in assessments:
            old_assessment = models.Assessment.objects.filter(pk=assessment.id).first()

            assessment.save()

            course.set_flex_assessments(assessment)

            if not old_assessment:
                assessment_created = True
                logger.info(
                    "%s created (default %s%%, min %s%%, max %s%%)",
                    assessment.title,
                    assessment.default,
                    assessment.min,
                    assessment.max,
                    extra=log_extra,
                )
            else:
                log_allocations = (
                    old_assessment.default,
                    old_assessment.min,
                    old_assessment.max,
                    assessment.default,
                    assessment.min,
                    assessment.max,
                )
                if log_allocations[:3] != log_allocations[3:]:
                    logger.info(
                        "%s updated "
                        "(default %s%%, min %s%%, max %s%%) "
                        "to (default %s%%, min %s%%, max %s%%)",
                        assessment.title,
                        *log_allocations,
                        extra=log_extra
                    )

        return assessment_created

    def _delete_assessments(self, course, assessments):
        assessments_to_delete = course.assessment_set.exclude(
            id__in=[assessment.id for assessment in assessments]
        )

        assessment_deleted = False
        if assessments_to_delete:
            assessment_deleted = True
            logger.info(
                "Deleted assessments: %s",
                ", ".join(assessments_to_delete.values_list("title", flat=True)),
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )
            assessments_to_delete.delete()

        return assessment_deleted

    def _reset_conflict_students(self, course, conflict_students):
        course.reset_students(conflict_students)

        for student in conflict_students:
            logger.info(
                "Reset flex allocations and comment for %s "
                "due to out of range allocations",
                student.display_name,
                extra={
                    "course": str(course),
                    "user": self.request.session["display_name"],
                },
            )

    def _reset_all_students(self, course):
        course.reset_all_students()

        logger.info(
            "Reset all student flex allocations and comments "
            "due to new or deleted assessment(s)",
            extra={"course": str(course), "user": self.request.session["display_name"]},
        )

    def _to_initial_dict(self, fields_str):
        """Converts assessment data for formset initial data

        Parameters
        ----------
        fields_str : str
            Assessment data as string

        Returns
        -------
        initial : dict
            Assessment formset initial data
        """

        if not fields_str:
            return []

        fields = json.loads(fields_str)
        initial = []
        names = ("title", "default", "min", "max")
        for values in fields:
            assessment_fields = {}
            for name, value in zip(names, values):
                assessment_fields[name] = value
            initial.append(assessment_fields)

        return initial


class OverrideStudentAssessmentView(views.InstructorFormView):
    """FormView for instructor overriding student flexible allocations"""

    template_name = "instructor/override_student_form.html"
    form_class = StudentAssessmentBaseForm

    def get_success_url(self):
        previous = self.request.GET.get("previous", "")
        if previous == "final":
            self.success_reverse_name = "instructor:final_grades"
        else:
            self.success_reverse_name = "instructor:percentage_list"

        return super().get_success_url()

    def get_context_data(self, **kwargs):
        """Adds the student name whose allocations are being overriden
        and previous page to the context

        Returns
        -------
        context : context
            Request context
        """

        context = super().get_context_data(**kwargs)
        student_name = get_object_or_404(
            models.UserProfile, pk=self.kwargs["pk"]
        ).display_name
        context["student_name"] = student_name

        previous = self.request.GET.get("previous", "")

        context["previous"] = previous

        return context

    def get_form_kwargs(self):
        """Adds user id and course id as keyword argument for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super().get_form_kwargs()
        user_id = self.kwargs["pk"]
        course_id = self.kwargs["course_id"]

        if not user_id or not course_id:
            raise PermissionDenied

        kwargs["user_id"] = user_id
        kwargs["course_id"] = course_id

        return kwargs

    def form_valid(self, form):
        """Validates form by checking if flex allocation is within range
        and updates flex assessments for student

        Parameters
        ----------
        form : StudentAssessmentBaseForm
            Flexible allocation data for assessments in course

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error in form
        """

        user_id = self.kwargs["pk"]
        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        if not user_id or not course_id:
            raise PermissionDenied

        assessment_fields = list(form.cleaned_data.items())
        # for assessment_id, flex in assessment_fields:
        #     assessment = models.Assessment.objects.get(pk=assessment_id)
        #     if flex > assessment.max:
        #         form.add_error(
        #             assessment_id,
        #             ValidationError("Flex should be less than or equal to max"),
        #         )
        #     elif flex < assessment.min:
        #         form.add_error(
        #             assessment_id,
        #             ValidationError("Flex should be greater than or equal to min"),
        #         )

        if form.errors:
            response = super().form_invalid(form)
            return response

        log_extra = {
            "course": str(course),
            "user": self.request.session["display_name"],
        }

        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id
            ).first()
            old_flex = flex_assessment.flex
            flex_assessment.flex = flex
            # Informs the database that the instructor updated the flex and not the student
            if old_flex != flex:
                flex_assessment.override = True
            flex_assessment.save()

            if old_flex is None:
                logger.info(
                    "Set %s flex for %s to %s%%",
                    flex_assessment.user.display_name,
                    assessment.title,
                    flex,
                    extra=log_extra,
                )
            elif old_flex != flex:
                logger.info(
                    "Updated %s flex for %s " "from %s%% to %s%%",
                    flex_assessment.user.display_name,
                    assessment.title,
                    old_flex,
                    flex,
                    extra=log_extra,
                )

        response = super().form_valid(form)
        return response


class ImportAssessmentView(views.InstructorFormView):
    """FormView for importing assessments"""

    template_name = "instructor/assessment_upload.html"
    form_class = AssessmentFileForm
    success_reverse_name = "instructor:instructor_form"

    def get_success_url(self):
        """Appends imported assessment data to url as parameter"""

        fields_str = json.dumps(self.fields, separators=(",", ":"))
        success_url = super().get_success_url() + "?initial={}".format(fields_str)

        return success_url

    def form_valid(self, form):
        """Validates import assessments form,
        sets url parameter for form data to be used on success callback

        Parameters
        ----------
        form : AssessmentFileForm
            Contains uploaded assessment data file

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error
        """

        file_header = self.request.FILES.get("assessments", None)
        if file_header is None:
            return super().form_invalid(form)
        encoded_file = TextIOWrapper(file_header.file, encoding=self.request.encoding)

        with encoded_file as csv_file:
            data = []
            reader = csv.reader(csv_file)
            headers = next(reader, None)
            if headers != ["Assessment", "Default", "Minimum", "Maximum"]:
                return super().form_invalid(form)

            for row in reader:
                if len(row) != 4:
                    return super().form_invalid(form)
                try:
                    int(row[1])
                    int(row[2])
                    int(row[3])
                except ValueError:
                    return super().form_invalid(form)

                data.append(row)

        self.fields = data

        course_id = self.kwargs["course_id"]
        course = models.Course.objects.get(pk=course_id)

        logger.info(
            "Successfully imported assessments (not yet saved)",
            extra={"course": str(course), "user": self.request.session["display_name"]},
        )

        return super().form_valid(form)


class InstructorHelp(views.InstructorTemplateView):
    template_name = "instructor/instructor_help.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)
        return response


def match_calendar_to_flex_dates(request, course_id):
    """
    Function based view that changes the calendar to match the flex dates before redirecting back to instructor_form
    """
    course = models.Course.objects.get(pk=course_id)
    if course.calendar_id is not None:
        calendar_event = FlexCanvas(request).get_calendar_event(course.calendar_id)
        calendar_event_old = calendar_event.end_at
        calendar_event.edit(
            calendar_event={
                "title": ("Flexible Assessment"),
                "start_at": course.close,
                "end_at": course.close,
                "all_day": True,
                "description": "If you have not made your choices by this deadline, your choices will be  <strong>automatically set to the default percentages</strong>",
            }
        )
        logger.info(
            "Calendar event with id %s updated from %s to %s",
            course.calendar_id,
            calendar_event_old,
            course.close,
            extra={
                "course": str(course),
                "user": request.session["display_name"],
            },
        )

    return HttpResponseRedirect(
        reverse("instructor:instructor_form", kwargs={"course_id": course_id})
    )


def match_flex_dates_to_calendar(request, course_id):
    """
    Function based view that changes the flex dates to match the calendar before redirecting back to instructor_form
    """
    course = models.Course.objects.get(pk=course_id)
    if course.calendar_id is not None:
        calendar_event = FlexCanvas(request).get_calendar_event(course.calendar_id)
        curr_start = course.open
        curr_end = course.close
        course.close = dateutil.parser.isoparse(calendar_event.end_at)
        course.save(update_fields=["close"])

        if course.close < course.open:
            course.open = course.close + dateutil.relativedelta.relativedelta(days=-1)
            course.save(update_fields=["open"])

        logger.info(
            "Updated flex availability " "from %s - %s to %s - %s",
            curr_start,
            curr_end,
            course.open,
            course.close,
            extra={
                "course": str(course),
                "user": request.session["display_name"],
            },
        )

    return HttpResponseRedirect(
        reverse("instructor:instructor_form", kwargs={"course_id": course_id})
    )
