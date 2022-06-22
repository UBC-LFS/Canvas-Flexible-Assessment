from django.contrib import admin

from . import models

admin.site.register(models.UserProfile)
admin.site.register(models.Course)
admin.site.register(models.UserCourse)
admin.site.register(models.Assessment)
admin.site.register(models.FlexAssessment)
admin.site.register(models.UserComment)
admin.site.register(models.AssignmentGroup)
