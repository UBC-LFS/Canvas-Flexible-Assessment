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

import fitz
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
        errors = []

        # get valid student IDs from database
        valid_student_ids = []
        students = self.get_queryset()
        for student in students:
            valid_student_ids.append(student.login_id)

        student_numbers = request.POST.getlist("student_number")
        multipliers = request.POST.getlist("multiplier")

        seen_ids = set()
        duplicate_ids = []

        # Check if data is formatted properly - if not, redirect back to form with error messages
        if len(student_numbers) != len(multipliers):
            errors.append(
                f"Number of student numbers does not equal number of multipliers"
            )
        elif len(student_numbers) == 0 or len(multipliers) == 0:
            errors.append(f"No accommodations entered")
        else:
            for sn, mult in zip(student_numbers, multipliers):
                if len(sn) != 8 or not sn.isdigit():
                    errors.append(f"Invalid student number format: {sn}")
                elif (
                    sn not in valid_student_ids
                ):  # comment out this condition when running tests
                    errors.append(f"Student not found in course: {sn}")

                if mult not in {"1.25", "1.5", "2.0"}:
                    errors.append(f"Invalid multiplier '{mult}' for student {sn}")

                if sn in seen_ids:
                    duplicate_ids.append(sn)
                else:
                    seen_ids.add(sn)

            for duplicate in duplicate_ids:
                errors.append(f"Duplicate entries found for student: {duplicate}")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("accommodations:accommodations_home", kwargs["course_id"])

        accommodations = list(zip(student_numbers, multipliers))
        request.session["accommodations"] = accommodations

        course = models.Course.objects.get(pk=course_id)

        for key, value in request.session.items():
            print("{} => {}".format(key, value))

        logger.info(
            "Instructor has uploaded accommodations (not yet submitted on Canvas) for "
            + str(len(accommodations))
            + " students",
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
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if not (f.name.lower().endswith(".pdf") and pdf_bytes.startswith(b"%PDF")):
                parsed_data.append(("error", f"{f.name} is not a PDF."))
                continue

            text = ""
            for page in doc:
                text += page.get_text()

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

        context["accommodations"] = accommodations
        context["accommodations_json"] = mark_safe(
            json.dumps(accommodations)
        )  # pass to template as json for javascript to use
        context["quizzes"] = quizzes
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
        quiz_list = canvas.get_quiz_data(course_id)

        request.session["quizzes"] = quiz_list

        response = super().get(request, *args, **kwargs)

        return response
