from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from django.contrib import messages

import flexible_assessment.class_views as views
import flexible_assessment.utils as utils

import json


class AccommodationsHome(views.InstructorListView):
    template_name = "accommodations/accommodations_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accommodations = self.request.session.get("accommodations", [])
        context["accommodations"] = accommodations
        context["accommodations_json"] = mark_safe(json.dumps(accommodations))
        return context

    def get(self, request, *args, **kwargs):
        if "accommodations" not in request.session:
            request.session["accommodations"] = []
        response = super().get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        course_id = self.kwargs["course_id"]
        errors = []

        valid_student_ids = []
        students = self.get_queryset()
        for student in students:
            valid_student_ids.append(student.login_id)

        # Handle raw POST data here (e.g. multiple student numbers and multipliers)
        student_numbers = request.POST.getlist("student_number")
        multipliers = request.POST.getlist("multiplier")

        # Check if data is formatted properly
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
                elif sn not in valid_student_ids:
                    errors.append(f"Student not found in course: {sn}")

                if mult not in {"1.25", "1.5", "2.0"}:
                    errors.append(f"Invalid multiplier '{mult}' for student {sn}")

            if len(student_numbers) != len(set(student_numbers)):
                errors.append(f"Duplicate student numbers exist")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("accommodations:accommodations_home", kwargs["course_id"])

        request.session["accommodations"] = list(zip(student_numbers, multipliers))

        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_quizzes", kwargs={"course_id": course_id}
            )
        )


def quizzes(request, *args, **kwargs):
    return HttpResponse(
        "<h1>Accommodations: "
        + str(request.session.get("accommodations", "no accommodations in session"))
        + "</h1>"
    )
