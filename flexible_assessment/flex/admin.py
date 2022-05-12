from django.contrib import admin
from .models import UserProfile, Course, UserCourse, Assessment, AssessmentCourse, FlexAssessment

admin.site.register(UserProfile)
admin.site.register(Course)
admin.site.register(UserCourse)
admin.site.register(Assessment)
admin.site.register(AssessmentCourse)
admin.site.register(FlexAssessment)
