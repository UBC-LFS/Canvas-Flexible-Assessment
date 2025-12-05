from abc import ABC, abstractmethod

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import (
    ImproperlyConfigured,
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect

from flexible_assessment.view_roles import Instructor, Student

from .models import Course, Roles, UserProfile, UserCourse


class ExportView(ABC):
    @abstractmethod
    def export_list(self):
        pass

    def get(self, request, *args, **kwargs):
        if self.kwargs.get("csv", False) or self.kwargs.get("log", False):
            return self.export_list()
        else:
            response = super().get(request, *args, **kwargs)
            return response


class GenericView(LoginRequiredMixin, UserPassesTestMixin):
    """Generic view for Instructor and Student views

    Attributes
    ----------
    allowed_view_role : ViewRole
        Used for defining the test function for UserPassesTesMixin
    raise_exception : bool
        From LoginRequiredMixin, set to True so that exception is
        thrown if user is not logged in
    """

    allowed_view_role = None
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = Course.objects.get(pk=self.kwargs["course_id"])
        return context

    def test_func(self):
        if not self.allowed_view_role:
            raise ImproperlyConfigured(
                "GenericView requires definition of 'allowed_view_role'"
            )
        course = get_object_or_404(Course, pk=self.kwargs["course_id"])
        allowed_to_access = self.allowed_view_role.permission_test(
            self.request.user, course
        )

        return allowed_to_access

    def handle_no_permission(self):
        """Try to redirect user to the homepage that they have the permissions for"""
        try:
            course_id = self.kwargs["course_id"]
            user_course = UserCourse.objects.get(
                course_id=course_id, user_id=self.request.user.user_id
            )
        except Exception as e:
            raise PermissionDenied(
                "You do not have the right permissions to view this page"
            )

        if user_course.role in Instructor.permitted_roles:
            messages.info(
                self.request,
                "You have been automatically redirected back to the page you have permissions to view (Instructor)",
            )
            return HttpResponseRedirect(
                reverse("instructor:instructor_home", kwargs={"course_id": course_id})
            )
        elif user_course.role in Student.permitted_roles:
            messages.info(
                self.request,
                "You have been automatically redirected back to the page you have permissions to view (Student)",
            )
            return HttpResponseRedirect(
                reverse("student:student_home", kwargs={"course_id": course_id})
            )
        else:
            raise PermissionDenied(
                "You do not have the right permissions to view this page"
            )


class TemplateView(GenericView, generic.TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["display_name"] = self.request.session.get("display_name", "")
        if context["display_name"] == "":
            context["display_name"] = UserProfile.objects.get(
                pk=self.request.session["_auth_user_id"]
            ).display_name
            self.request.session["display_name"] = context["display_name"]

        return context


class InstructorTemplateView(TemplateView):
    allowed_view_role = Instructor


class StudentTemplateView(TemplateView):
    allowed_view_role = Student


class ListView(GenericView, generic.ListView):
    pass


class InstructorListView(ListView):
    allowed_view_role = Instructor
    model = UserProfile
    context_object_name = "student_list"

    def get_queryset(self):
        """QuerySet is students for current course"""

        course_id = self.kwargs["course_id"]
        queryset = UserProfile.objects.filter(
            usercourse__role=Roles.STUDENT, usercourse__course__id=course_id
        )
        return queryset


class FormView(GenericView, generic.FormView):
    success_reverse_name = None

    def get_success_url(self):
        if not self.success_reverse_name:
            raise ImproperlyConfigured(
                "No success reverse name to redirect to."
                " Provide success_reverse_name."
            )
        return reverse_lazy(
            self.success_reverse_name, kwargs={"course_id": self.kwargs["course_id"]}
        )


class InstructorFormView(FormView):
    allowed_view_role = Instructor


class StudentFormView(FormView):
    allowed_view_role = Student
