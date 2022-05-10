from django.contrib import admin
from .models import User, Course, UserCourse, Assessment, AssessmentCourse, FlexAssessment

admin.site.register(User)
admin.site.register(Course)
admin.site.register(UserCourse)
admin.site.register(Assessment)
admin.site.register(AssessmentCourse)
admin.site.register(FlexAssessment)