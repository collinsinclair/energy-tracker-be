from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DailyBalanceView,
    DailyBalancesView,
    ExpenditureViewSet,
    IntakeViewSet,
    WeightViewSet,
    RemainingDailyCalories,
)

router = DefaultRouter()
router.register(r"intakes", IntakeViewSet)
router.register(r"expenditures", ExpenditureViewSet)
router.register(r"weights", WeightViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("daily_balance/", DailyBalanceView.as_view(), name="daily-balance"),
    path("daily_balances/", DailyBalancesView.as_view(), name="daily-balances"),
    path(
        "remaining_daily_calories/",
        RemainingDailyCalories.as_view(),
        name="remaining-daily-calories",
    ),
]
