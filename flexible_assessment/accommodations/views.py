from django.shortcuts import render
from django.http import HttpResponse

import flexible_assessment.class_views as views
 
class AccommodationsHome(views.InstructorTemplateView):
    template_name = "accommodations/accommodations_home.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        return response