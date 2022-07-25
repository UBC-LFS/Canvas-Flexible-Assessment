from abc import ABC, abstractmethod

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from django.views import generic

from flexible_assessment.view_roles import Instructor, Student

from .models import Course, Roles, UserProfile


class ExportView(ABC):
    @abstractmethod
    def export_list(self):
        pass

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            return self.export_list()
        else:
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
        context['course'] = Course.objects.get(pk=self.kwargs['course_id'])
        return context

    def test_func(self):
        if not self.allowed_view_role:
            raise ImproperlyConfigured(
                "GenericView requires definition of 'allowed_view_role'")
        return self.allowed_view_role.permission_test(self.request.user)


class TemplateView(GenericView, generic.TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['display_name'] = self.request.session.get('display_name', '')
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
    context_object_name = 'student_list'

    def get_queryset(self):
        """QuerySet is students for current course"""

        course_id = self.kwargs['course_id']
        queryset = UserProfile.objects.filter(
            role=Roles.STUDENT, usercourse__course__id=course_id)
        return queryset


class FormView(GenericView, generic.FormView):
    success_reverse_name = None

    def get_success_url(self):
        if not self.success_reverse_name:
            raise ImproperlyConfigured(
                "No success reverse name to redirect to."
                " Provide success_reverse_name.")
        return reverse_lazy(self.success_reverse_name,
                            kwargs={'course_id': self.kwargs['course_id']})


class InstructorFormView(FormView):
    allowed_view_role = Instructor


class StudentFormView(FormView):
    allowed_view_role = Student
