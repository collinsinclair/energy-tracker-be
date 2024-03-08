from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExpenditureViewSet, IntakeViewSet, WeightViewSet

router = DefaultRouter()
router.register(r"intakes", IntakeViewSet)
router.register(r"expenditures", ExpenditureViewSet)
router.register(r"weights", WeightViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
