from django.contrib import admin

from .models import UserComment, UserProfile, Course, UserCourse, Assessment, FlexAssessment

admin.site.register(UserProfile)
admin.site.register(Course)
admin.site.register(UserCourse)
admin.site.register(Assessment)
admin.site.register(FlexAssessment)
admin.site.register(UserComment)
