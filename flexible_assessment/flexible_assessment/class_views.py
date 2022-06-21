from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import generic
from django.core.exceptions import ImproperlyConfigured

from models import Course


class GenericView(LoginRequiredMixin, UserPassesTestMixin):
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
    pass


class ListView(GenericView, generic.ListView):
    pass


class FormView(GenericView, generic.FormView):
    pass
