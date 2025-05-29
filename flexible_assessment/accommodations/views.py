from django.shortcuts import render
from django.urls import reverse
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.views.decorators.http import require_POST

import flexible_assessment.class_views as views
import flexible_assessment.models as models
import flexible_assessment.utils as utils

from flexible_assessment.models import Course

import pypdf
import io
import re
import json
import logging

from accommodations.canvas_api import AccommodationsCanvas


logger = logging.getLogger(__name__)


class AccommodationsHome(views.AccommodationsListView):
    template_name = "accommodations/accommodations_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accommodations = self.request.session.get("accommodations", [])
        context["accommodations"] = accommodations
        context["accommodations_json"] = mark_safe(
            json.dumps(accommodations)
        )  # pass to template as json for javascript to use
        context["course"] = Course.objects.get(pk=self.kwargs["course_id"])
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # if redirected, update students in database
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)
        return response

    def post(self, request, *args, **kwargs):
        course_id = self.kwargs["course_id"]

        # Load valid student data from DB
        students = self.get_queryset()
        valid_student_ids = set(s.login_id for s in students)
        login_id_to_user_id = {s.login_id: s.user_id for s in students}

        student_numbers = request.POST.getlist("student_number")
        multipliers = request.POST.getlist("multiplier")

        if not student_numbers or not multipliers:
            messages.error(request, "No accommodations entered.")
            return redirect("accommodations:accommodations_home", course_id)

        if len(student_numbers) != len(multipliers):
            messages.error(
                request,
                "Number of student numbers does not equal number of multipliers.",
            )
            return redirect("accommodations:accommodations_home", course_id)

        seen_ids = set()
        accommodations = []
        errors = []

        for sn, mult in zip(student_numbers, multipliers):
            if len(sn) != 8 or not sn.isdigit():
                errors.append(f"Invalid student number format: {sn}")
            elif sn not in valid_student_ids:
                errors.append(f"Student not found in course: {sn}")
            elif mult not in {"1.25", "1.5", "2.0"}:
                errors.append(f"Invalid multiplier '{mult}' for student {sn}")
            elif sn in seen_ids:
                errors.append(f"Duplicate entry for student: {sn}")
            else:
                accommodations.append((sn, mult, login_id_to_user_id[sn]))
                seen_ids.add(sn)

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("accommodations:accommodations_home", course_id)

        request.session["accommodations"] = accommodations

        course = models.Course.objects.get(pk=course_id)
        logger.info(
            f"Instructor uploaded accommodations for {len(accommodations)} students",
            extra={"course": str(course), "user": request.session["display_name"]},
        )

        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_quizzes", kwargs={"course_id": course_id}
            )
        )


@require_POST
def upload_pdfs(request, course_id):
    uploaded_files = request.FILES.getlist("pdf_files")
    parsed_data = []

    for f in uploaded_files:
        try:
            # Read file into memory
            pdf_bytes = f.read()

            if not (f.name.lower().endswith(".pdf") and pdf_bytes.startswith(b"%PDF")):
                parsed_data.append(("error", f"{f.name} is not a PDF."))
                continue

            # Load the PDF from bytes
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            # Match 8-digit student number
            student_match = re.search(r"\b\d{8}\b", text)
            # Match multiplier (1.25x, 1.5x, 2x, etc.)
            multiplier_match = re.search(
                r"\b(1\.25|1\.5|2(?:\.0)?)x\b", text, re.IGNORECASE
            )

            student_number = student_match.group() if student_match else None
            multiplier = multiplier_match.group(1) if multiplier_match else None

            if multiplier == "2":
                multiplier = "2.0"

            if student_number and multiplier:
                parsed_data.append((student_number, multiplier))
            else:
                parsed_data.append(
                    ("error", f"{f.name} is missing student or multiplier.")
                )

        except Exception as e:
            parsed_data.append(("error", f"{f.name} failed to process: {str(e)}"))

    print(parsed_data)

    return JsonResponse({"results": parsed_data})


class AccommodationsQuizzes(views.AccommodationsListView):
    template_name = "accommodations/accommodations_quizzes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accommodations = self.request.session.get("accommodations", [])
        quizzes = self.request.session.get("quizzes", [])
        unavailable_quizzes = self.request.session.get("unavailable_quizzes", [])
        selected_quizzes = self.request.session.get("selected_quizzes", [])

        context["accommodations"] = accommodations
        context["quizzes"] = quizzes
        context["unavailable_quizzes"] = unavailable_quizzes
        context["selected_quizzes"] = selected_quizzes
        context["course"] = Course.objects.get(pk=self.kwargs["course_id"])
        return context

    def get(self, request, *args, **kwargs):
        # should require that accommodations exist in context data - if not, redirect back to home
        course_id = self.kwargs["course_id"]
        accommodations = request.session.get("accommodations", None)

        # if redirected, update students in database
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)

        if accommodations == None or accommodations == []:
            messages.error(
                request,
                "Please set student accommodations before trying to access the quiz page.",
            )
            return HttpResponseRedirect(
                reverse(
                    "accommodations:accommodations_home",
                    kwargs={"course_id": course_id},
                )
            )

        canvas = AccommodationsCanvas(request)
        quiz_list, unavailable_quiz_list = canvas.get_quiz_data(course_id)

        request.session["quizzes"] = quiz_list
        request.session["unavailable_quizzes"] = unavailable_quiz_list

        response = super().get(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        course_id = self.kwargs["course_id"]
        quiz_list = request.session["quizzes"]
        selected_quiz_ids = request.POST.getlist("selected_quizzes")
        selected_quizzes = list(
            filter(lambda quiz: str(quiz["id"]) in selected_quiz_ids, quiz_list)
        )

        if len(selected_quizzes) == 0:
            messages.error(
                request,
                "No quizzes selected - please select at least one quiz before submitting.",
            )
            return HttpResponseRedirect(
                reverse(
                    "accommodations:accommodations_quizzes",
                    kwargs={"course_id": course_id},
                )
            )

        request.session["selected_quizzes"] = selected_quizzes

        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_confirm", kwargs={"course_id": course_id}
            )
        )


class AccommodationsConfirm(views.AccommodationsListView):
    template_name = "accommodations/accommodations_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        multiplier_student_groups = self.request.session.get(
            "multiplier_student_groups", []
        )
        multiplier_quiz_groups = self.request.session.get("multiplier_quiz_groups", {})
        selected_quizzes = self.request.session.get("selected_quizzes", [])

        context["multiplier_student_groups"] = multiplier_student_groups
        context["multiplier_quiz_groups"] = multiplier_quiz_groups
        context["selected_quizzes"] = selected_quizzes
        context["course"] = Course.objects.get(pk=self.kwargs["course_id"])
        return context

    def get(self, request, *args, **kwargs):
        # should require that accommodations, selected quizzes exist in context data - if not, redirect back to home
        course_id = self.kwargs["course_id"]
        accommodations = request.session.get("accommodations", None)
        selected_quizzes = request.session.get("selected_quizzes", None)

        # if redirected, update students in database
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)

        if accommodations == None or accommodations == []:
            messages.error(
                request,
                "Please set student accommodations before trying to access the submission page.",
            )
            return HttpResponseRedirect(
                reverse(
                    "accommodations:accommodations_home",
                    kwargs={"course_id": course_id},
                )
            )
        elif selected_quizzes == None or selected_quizzes == []:
            messages.error(
                request,
                "Please select at least one quiz before trying to access the submission page.",
            )
            return HttpResponseRedirect(
                reverse(
                    "accommodations:accommodations_quizzes",
                    kwargs={"course_id": course_id},
                )
            )

        students = self.get_queryset()
        canvas = AccommodationsCanvas(request)

        multiplier_student_groups = canvas.get_multiplier_student_groups(
            accommodations, students
        )

        multiplier_quiz_groups = canvas.get_multiplier_quiz_groups(selected_quizzes)

        existing_accommodations = canvas.get_existing_accommodations(
            accommodations, students, multiplier_quiz_groups, course_id
        )  # from canvas, I can get the list of accommodations and the students with existing accommodations

        request.session["multiplier_student_groups"] = multiplier_student_groups
        request.session["multiplier_quiz_groups"] = multiplier_quiz_groups
        request.session["existing_accommodations"] = existing_accommodations

        response = super().get(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        course_id = self.kwargs["course_id"]
        multiplier_student_groups = request.session["multiplier_student_groups"]
        multiplier_quiz_groups = request.session["multiplier_quiz_groups"]

        canvas = AccommodationsCanvas(request)
        multiplier_quiz_groups_results, time_extension_status = (
            canvas.add_time_extensions(
                multiplier_student_groups, multiplier_quiz_groups, course_id
            )
        )
        multiplier_quiz_groups_results, availabilities_status = (
            canvas.add_availabilities(
                multiplier_student_groups, multiplier_quiz_groups_results, course_id
            )
        )

        if time_extension_status is False:
            messages.error(
                request,
                "Errors were encountered when extending time limits.",
            )
        if availabilities_status is False:
            messages.error(
                request,
                "Errors were encountered when extending end dates.",
            )
        if time_extension_status and availabilities_status:
            messages.success(
                request,
                "All accommodations applied successfully.",
            )

        results_string = ""
        for accommodation, quizzes in multiplier_quiz_groups_results.items():
            results_string += "<h3>" + str(accommodation) + "</h3>" + "<br>"
            for quiz in quizzes:
                results_string += (
                    "-----"
                    + quiz["title"]
                    + " (time limit status: "
                    + quiz["time_limit_status"]
                    + "), (lock at status: "
                    + quiz["lock_at_status"]
                    + ")"
                    + "<br>"
                )

        request.session["multiplier_quiz_groups_results"] = (
            multiplier_quiz_groups_results
        )

        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_summary", kwargs={"course_id": course_id}
            )
        )


class AccommodationsSummary(views.AccommodationsListView):
    template_name = "accommodations/accommodations_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        multiplier_student_groups = self.request.session.get(
            "multiplier_student_groups", []
        )
        multiplier_quiz_groups_results = self.request.session.get(
            "multiplier_quiz_groups_results", {}
        )
        selected_quizzes = self.request.session.get("selected_quizzes", [])

        context["multiplier_student_groups"] = multiplier_student_groups
        context["multiplier_quiz_groups_results"] = multiplier_quiz_groups_results
        context["selected_quizzes"] = selected_quizzes
        context["course"] = Course.objects.get(pk=self.kwargs["course_id"])
        return context

    def get(self, request, *args, **kwargs):
        # should require that accommodations, selected quizzes exist in context data - if not, redirect back to home
        course_id = self.kwargs["course_id"]
        multiplier_quiz_groups_results = request.session.get(
            "multiplier_quiz_groups_results", None
        )

        # if redirected, update students in database
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)

        if (
            multiplier_quiz_groups_results == None
            or multiplier_quiz_groups_results == {}
        ):
            messages.error(
                request,
                "You can only access the summary page after confirming and submitting accommodations.",
            )
            return HttpResponseRedirect(
                reverse(
                    "accommodations:accommodations_home",
                    kwargs={"course_id": course_id},
                )
            )

        response = super().get(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        # post should clear session data
        course_id = self.kwargs["course_id"]
        login_data = [
            "user_id",
            "login_id",
            "display_name",
            "_auth_user_id",
            "_auth_user_backend",
            "_auth_user_hash",
        ]  # keep these fields so user remains logged in
        for key in list(
            request.session.keys()
        ):  # cast as list since modifying size of iterator breaks
            if key not in login_data:
                del request.session[key]
        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_home", kwargs={"course_id": course_id}
            )
        )
