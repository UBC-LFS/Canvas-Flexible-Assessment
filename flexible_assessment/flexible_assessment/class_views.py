from django.views import generic
from .models import Course


class GenericView():
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = Course.objects.get(pk=self.kwargs['course_id'])
        return context


class TemplateView(GenericView, generic.TemplateView):
    pass


class ListView(GenericView, generic.ListView):
    pass


class FormView(GenericView, generic.FormView):
    pass
