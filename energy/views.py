import datetime

from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Expenditure, Intake, Weight
from .serializers import ExpenditureSerializer, IntakeSerializer, WeightSerializer


class IntakeViewSet(viewsets.ModelViewSet):
    queryset = Intake.objects.all()
    serializer_class = IntakeSerializer

    @action(detail=False, methods=["get"])
    def daily_sum(self, request):
        date_str = request.query_params.get("date", None)
        if date_str is None:
            date = timezone.now().date()
        else:
            from django.utils.dateparse import parse_date

            date = parse_date(date_str)
            if date is None:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."}, status=400
                )
        datetime_start = datetime.datetime.combine(date, datetime.time.min)
        datetime_end = datetime.datetime.combine(date, datetime.time.max)
        sum_calories = (
            self.queryset.filter(
                timestamp__range=(datetime_start, datetime_end)
            ).aggregate(Sum("calories"))["calories__sum"]
            or 0
        )
        return Response({"date": date.isoformat(), "total_calories": sum_calories})

    @action(detail=False, methods=["get"])
    def daily_sums(self, request):
        daily_calories = (
            self.queryset.annotate(date=TruncDay("timestamp"))
            .values("date")
            .annotate(total_calories=Sum("calories"))
            .order_by("date")
        )
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
