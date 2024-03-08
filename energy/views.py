import datetime

from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expenditure, Intake, Weight
from .serializers import ExpenditureSerializer, IntakeSerializer, WeightSerializer


class DateRangeOperationsMixin:
    def get_date_from_request(self, request):
        date_str = request.query_params.get("date", None)
        if date_str is None:
            return timezone.now().date()
        else:
            date = parse_date(date_str)
            if date is None:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            return date

    def get_datetime_range_for_date(self, date):
        datetime_start = datetime.datetime.combine(date, datetime.time.min)
        datetime_end = datetime.datetime.combine(date, datetime.time.max)
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
        # Ensure we're working with dates in the same format
        daily_intakes = (
            self.aggregate_daily_calories(Intake.objects.all())
            .annotate(date_only=TruncDay("date"))
            .order_by("date_only")
        )  # Ensure this aligns with how you aggregate daily calories
        # Since Expenditure uses a DateField, we can directly use 'date' for aggregation without modification
        daily_expenditures = (
            Expenditure.objects.values("date")  # Direct grouping by 'date' field
            .annotate(total_expenditure=Sum("calories"))
            .order_by("date")
        )
        expenditures_dict = {
            item["date"]: item["total_expenditure"] for item in daily_expenditures
        }
        balances_data = []
        for intake in daily_intakes:
            date = intake[
                "date"
            ].date()  # Convert datetime to date to match Expenditure's date field
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
