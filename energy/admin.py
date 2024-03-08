from django.contrib import admin

from .models import CalorieExpenditure, Food, Weight

admin.site.register(Food)
admin.site.register(CalorieExpenditure)
admin.site.register(Weight)
