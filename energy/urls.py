from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CalorieExpenditureViewSet, FoodViewSet, WeightViewSet

router = DefaultRouter()
router.register(r"foods", FoodViewSet)
router.register(r"calorie_expenditures", CalorieExpenditureViewSet)
router.register(r"weights", WeightViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
