from django.contrib import admin

from .models import Expenditure, Intake, UserProfile, Weight

admin.site.register(Intake)
admin.site.register(Expenditure)
admin.site.register(Weight)
admin.site.register(UserProfile)
