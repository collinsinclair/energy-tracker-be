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
        """
        Extracts a date from the given request object's query parameters. If no date is provided,
        it returns the current date. The function expects the date in the 'YYYY-MM-DD' format.

        @param request: The HttpRequest object containing query parameters.
        @return: A datetime.date object representing the extracted or current date.
        @raise ValueError: If the date format is invalid or cannot be parsed.
        """
        date_str = request.query_params.get("date", None)
        if date_str is None:
            return timezone.now().date()
        else:
            date = parse_date(date_str)
            if date is None:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            return date

    def get_datetime_range_for_date(self, date):
        """
        Creates a datetime range for a given date, starting at the beginning of the day (00:00:00)
        and ending at the end of the day (23:59:59.999999).

        @param date: A datetime.date object for which the datetime range is needed.
        @return: A tuple containing two datetime.datetime objects representing the start and end
                 of the given date.
        """
        datetime_start = datetime.datetime.combine(date, datetime.time.min)
        datetime_end = datetime.datetime.combine(date, datetime.time.max)
        return datetime_start, datetime_end

    def aggregate_calories_for_date_range(self, model, datetime_start, datetime_end):
        """
        Aggregates the sum of calories for a given model's objects that fall within a specific
        datetime range.

        @param model: The Django model class to query against.
        @param datetime_start: A datetime.datetime object representing the start of the range.
        @param datetime_end: A datetime.datetime object representing the end of the range.
        @return: The sum of calories for objects within the specified datetime range.
                 Returns 0 if no objects are found.
        """
        return (
            model.objects.filter(
                timestamp__range=(datetime_start, datetime_end)
            ).aggregate(Sum("calories"))["calories__sum"]
            or 0
        )

    def aggregate_daily_calories(self, queryset):
        """
        Aggregates daily calories from a queryset, grouping the results by date and summing
        the calories for each date.

        @param queryset: A Django queryset of objects that have a 'timestamp' and 'calories' field.
        @return: A QuerySet containing dictionaries with 'date' and 'total_calories' keys,
                 representing the sum of calories for each day present in the input queryset.
        """
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
        """
        Provides the sum of calories consumed for a specified date, extracted from the request's
        query parameters. If no date is provided, it defaults to the current date. This method
        handles invalid date format errors and returns the total calories for the given date.

        @param request: The HttpRequest object containing query parameters, including an optional
                        'date' parameter in 'YYYY-MM-DD' format.
        @return: A Response object containing the 'date' and 'total_calories' for the specified date.
                 Returns a 400 error response if the date format is invalid.
        """
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
        """
        Aggregates and returns the daily sums of calories consumed for each day available in the
        queryset. This method does not require any date to be provided in the request's query
        parameters, as it calculates and returns the sum of calories for all dates present in the
        queryset.

        @param request: The HttpRequest object, used to access any query parameters if necessary.
                        This method does not use query parameters directly.
        @return: A Response object containing a list of dictionaries, each with a 'date' and
                 'total_calories' key, representing the sum of calories consumed for each day.
        """
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
        """
        Calculates and returns the daily balance of calories for a specified date by subtracting the
        total calorie expenditure from the total calorie intake. The date is extracted from the
        request's query parameters. If no date is provided, it defaults to the current date. This
        method also handles invalid date format errors by returning an error response.

        @param request: The HttpRequest object containing query parameters, including an optional
                        'date' parameter in 'YYYY-MM-DD' format.
        @return: A Response object containing the 'date', 'total_intake' calories, 'total_expenditure'
                 calories, and the resulting 'balance' of calories for the specified date. If the
                 date format is invalid, returns a 400 error response with the error message.
        """
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
        """
        Retrieves and calculates the daily balances of calories for all available dates by
        comparing the total calorie intake against the total calorie expenditure for each day.
        This endpoint aggregates calorie data across all dates present in the Intake and
        Expenditure models, computes the balance for each day, and returns a list of daily
        balances.

        @param request: The HttpRequest object. This method does not use any query parameters
                        from the request, as it operates over all available data.
        @return: A Response object containing a list of dictionaries. Each dictionary represents
                 a day's data with the keys 'date', 'total_intake', 'total_expenditure', and
                 'balance', indicating the day's date, total calorie intake, total calorie
                 expenditure, and the net balance of calories, respectively.
        """
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
