from django.shortcuts import render
import flexible_assessment.class_views as views
import flexible_assessment.utils as utils

class DueDatesHome(views.InstructorTemplateView):
    template_name = "due_dates/due_dates_home.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        login_redirect = request.GET.get("login_redirect")
        if login_redirect:
            course = self.get_context_data().get("course", "")
            utils.update_students(request, course)
        return response