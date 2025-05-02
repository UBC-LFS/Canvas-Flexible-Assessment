from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect

import flexible_assessment.class_views as views


class AccommodationsHome(views.InstructorTemplateView):
    template_name = "accommodations/accommodations_home.html"

    def get(self, request, *args, **kwargs):
        # todo - should initialize session with accomodations list
        # each accommodation is a tuple of student number: multiplier
        if request.session.has_key("student_numbers"):
            print("get: " + str(request.session["student_numbers"]))
        response = super().get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        if request.session.has_key("student_numbers"):
            print("post: " + str(request.session["student_numbers"]))
        course_id = self.kwargs["course_id"]

        # Handle raw POST data here (e.g. multiple student numbers and multipliers)
        student_numbers = request.POST.getlist("student_number")
        multipliers = request.POST.getlist("multiplier")

        request.session["student_numbers"] = student_numbers

        # Check if data is formatted properly
        if len(student_numbers) != len(multipliers):
            print("Number of student numbers is not equal to multiplier")

        if len(student_numbers) == 0 or len(multipliers) == 0:
            print("No accommodations entered")

        for sn, mult in zip(student_numbers, multipliers):
            if len(sn) != 8 or not sn.isdigit():
                print("Student number " + str(sn) + " invalid")

            if mult not in {"1.25", "1.5", "2.0"}:
                print("Multiplier " + str(mult) + " invalid")

        # Check if students exist in Canvas - can probably reuse database entries here

        return HttpResponseRedirect(
            reverse(
                "accommodations:accommodations_quizzes", kwargs={"course_id": course_id}
            )
        )


def quizzes(request, *args, **kwargs):
    return HttpResponse(
        "<h1>Student numbers: " + str(request.session["student_numbers"]) + "</h1>"
    )
