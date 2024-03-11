import datetime

from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
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


class DateRangeOperationsMixin:
    def get_date_from_request(self, request):
        date_str = request.query_params.get("date", None)
        if date_str is None:
            return timezone.localtime().date()
        else:
            date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            if date is None:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            return date

    def get_datetime_range_for_date(self, date):
        datetime_start = timezone.make_aware(
            datetime.datetime.combine(date, datetime.time.min)
        )
        datetime_end = timezone.make_aware(
            datetime.datetime.combine(date, datetime.time.max)
        )
        return datetime_start, datetime_end

    def aggregate_calories_for_date_range(self, model, datetime_start, datetime_end):
        return (
            model.objects.filter(
                timestamp__range=(datetime_start, datetime_end)
            ).aggregate(Sum("calories"))["calories__sum"]
            or 0
        )

    def aggregate_daily_calories(self, queryset):
        return (
            queryset.annotate(date=TruncDay("timestamp"))
            .values("date")
            .annotate(total_calories=Sum("calories"))
            .order_by("date")
        )


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


class RemainingDailyCalories(APIView, DateRangeOperationsMixin):
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

        user_profile = UserProfile.objects.first()
        remaining_calories = (
            total_expenditure + user_profile.goal_daily_calorie_delta - total_intake
        )

        return Response(
            {
                "date": date.isoformat(),
                "remaining_calories": remaining_calories,
                "goal_daily_calorie_delta": user_profile.goal_daily_calorie_delta,  # Added line
            }
        )


date_range_ops = DateRangeOperationsMixin()


@api_view(["GET"])
def daily_summary(request):
    try:
        date = date_range_ops.get_date_from_request(request)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    datetime_start, datetime_end = date_range_ops.get_datetime_range_for_date(date)
    total_intake = date_range_ops.aggregate_calories_for_date_range(
        Intake, datetime_start, datetime_end
    )
    expenditure_record = Expenditure.objects.filter(date=date).aggregate(
        total_expenditure=Sum("calories")
    )
    total_expenditure = expenditure_record.get("total_expenditure", 0) or 0
    user_profile = UserProfile.objects.first()
    goal_daily_calorie_delta = user_profile.goal_daily_calorie_delta
    calorie_goal = total_expenditure + goal_daily_calorie_delta
    remaining_calories = calorie_goal - total_intake
    todays_intakes = Intake.objects.filter(
        timestamp__range=(datetime_start, datetime_end)
    )
    todays_intakes_data = [
        {
            "id": intake.id,
            "label": intake.label,
            "calories": intake.calories,
            "timestamp": intake.timestamp,
        }
        for intake in todays_intakes
    ]
    summary_data = {
        "date": date.isoformat(),
        "total_calories_consumed": total_intake,
        "total_expenditure": total_expenditure,
        "calorie_goal": calorie_goal,
        "remaining_calories_until_goal": remaining_calories,
        "todays_intakes": todays_intakes_data,  # Include today's intakes data
    }
    return Response(summary_data)
