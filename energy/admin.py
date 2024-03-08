from django.contrib import admin

from .models import Food, CalorieExpenditure, Weight

admin.site.register(Food)
admin.site.register(CalorieExpenditure)
admin.site.register(Weight)
