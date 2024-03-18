# energy/views.py

from django.apps import apps
from django.db.models import Sum
from django.db.models.functions import TruncDay
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expenditure, Intake, UserProfile, Weight
from .serializers import (
    ExpenditureSerializer,
    IntakeSerializer,
    WeightSerializer,
)
from .utils import DateRangeOperationsMixin


class IntakeViewSet(viewsets.ModelViewSet, DateRangeOperationsMixin):
    queryset = Intake.objects.all()
    serializer_class = IntakeSerializer

    @action(detail=False, methods=["get"])
    def daily_sum(self, request):
        try:
            date = self.get_date_from_request(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        datetime_start, datetime_end = self.get_datetime_range_for_date(date)
        sum_calories = self.aggregate_calories_for_date_range(
            self.queryset.model, datetime_start, datetime_end
        )
        return Response({"date": date.isoformat(), "total_calories": sum_calories})

    @action(detail=False, methods=["get"])
    def daily_sums(self, request):
        daily_calories = self.aggregate_daily_calories(self.queryset)
        data = [
            {"date": item["date"].isoformat(), "total_calories": item["total_calories"]}
            for item in daily_calories
        ]
        return Response(data)

    @action(detail=False, methods=["get"])
    def todays_intakes(self, request):
        try:
            date = self.get_date_from_request(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        datetime_start, datetime_end = self.get_datetime_range_for_date(date)
        todays_intakes = self.queryset.filter(
            timestamp__range=(datetime_start, datetime_end)
        )
        serializer = self.get_serializer(todays_intakes, many=True)
        return Response(serializer.data)


class ExpenditureViewSet(viewsets.ModelViewSet):
    queryset = Expenditure.objects.all()
    serializer_class = ExpenditureSerializer


class WeightViewSet(viewsets.ModelViewSet):
    queryset = Weight.objects.all()
    serializer_class = WeightSerializer


class DailyBalanceView(APIView, DateRangeOperationsMixin):
    def get(self, request):
        try:
            date = self.get_date_from_request(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        datetime_start, datetime_end = self.get_datetime_range_for_date(date)
        total_intake = self.aggregate_calories_for_date_range(
            Intake, datetime_start, datetime_end
        )
        expenditure_record = Expenditure.objects.filter(date=date).first()
        total_expenditure = expenditure_record.calories if expenditure_record else 0
        balance = total_intake - total_expenditure
        return Response(
            {
                "date": date.isoformat(),
                "total_intake": total_intake,
                "total_expenditure": total_expenditure,
                "balance": balance,
            }
        )


class DailyBalancesView(APIView, DateRangeOperationsMixin):
    def get(self, request):
        daily_intakes = (
            self.aggregate_daily_calories(Intake.objects.all())
            .annotate(date_only=TruncDay("date"))
            .order_by("date_only")
        )
        daily_expenditures = (
            Expenditure.objects.values("date")
            .annotate(total_expenditure=Sum("calories"))
            .order_by("date")
        )
        expenditures_dict = {
            item["date"]: item["total_expenditure"] for item in daily_expenditures
        }
        balances_data = []
        for intake in daily_intakes:
            date = intake["date"].date()
            total_intake = intake["total_calories"]
            total_expenditure = expenditures_dict.get(date, 0)
            balance = total_intake - total_expenditure
            balances_data.append(
                {
                    "date": date.isoformat(),
                    "total_intake": total_intake,
                    "total_expenditure": total_expenditure,
                    "balance": balance,
                }
            )
        return Response(balances_data)


date_range_ops = DateRangeOperationsMixin()


@api_view(["GET"])
def daily_summary(request):
    try:
        date = date_range_ops.get_date_from_request(request)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    datetime_start, datetime_end = date_range_ops.get_datetime_range_for_date(date)
    Intake = apps.get_model("energy", "Intake")
    Expenditure = apps.get_model("energy", "Expenditure")
    UserProfile = apps.get_model("energy", "UserProfile")

    # get all the data
    total_intake = date_range_ops.aggregate_calories_for_date_range(
        Intake, datetime_start, datetime_end
    )
    total_expenditure = Expenditure.objects.filter(date=date).first().calories
    user_profile = UserProfile.objects.first()
    initial_goal = user_profile.goal_daily_calorie_delta
    previous_day_calorie_surplus = user_profile.previous_day_surplus_calories

    # do calculations
    adjusted_goal = initial_goal - previous_day_calorie_surplus
    remaining_calories = total_expenditure + adjusted_goal - total_intake

    summary_data = {
        "date": date.isoformat(),
        "total_intake": total_intake,
        "total_expenditure": total_expenditure,
        "initial_goal": initial_goal,
        "previous_day_calorie_surplus": previous_day_calorie_surplus,
        "adjusted_goal": adjusted_goal,
        "remaining_calories": remaining_calories,
    }
    return Response(summary_data)
