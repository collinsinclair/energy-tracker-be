# energy/utils.py
import datetime
from datetime import timedelta

from django.apps import apps
from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils import timezone


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

    def get_adjusted_goal_for_date(self, date):
        UserProfile = apps.get_model("energy", "UserProfile")
        Expenditure = apps.get_model("energy", "Expenditure")
        user_profile = UserProfile.objects.first()
        expenditure_record = Expenditure.objects.filter(date=date).first()
        total_expenditure = expenditure_record.calories if expenditure_record else 0
        adjusted_goal = (
            total_expenditure
            + user_profile.goal_daily_calorie_delta
            - user_profile.adjustment
        )
        return adjusted_goal


date_range_ops = DateRangeOperationsMixin()


def update_remaining_calories_adjustment(date_input):
    if not isinstance(date_input, datetime.datetime):
        date_input = datetime.datetime.combine(date_input, datetime.datetime.min.time())
    if timezone.is_naive(date_input):
        date_input = timezone.make_aware(date_input, timezone.get_default_timezone())
    Intake = apps.get_model("energy", "Intake")
    Expenditure = apps.get_model("energy", "Expenditure")
    UserProfile = apps.get_model("energy", "UserProfile")
    user_profile = UserProfile.objects.first()
    goal_delta_per_day = user_profile.goal_daily_calorie_delta
    earliest_intake_record = Intake.objects.order_by("timestamp").first()
    earliest_expenditure_record = Expenditure.objects.order_by("date").first()
    if earliest_intake_record and earliest_expenditure_record:
        earliest_date = min(
            earliest_intake_record.timestamp.date(),
            earliest_expenditure_record.date
        )
    else:
        earliest_date = date_input.date() - datetime.timedelta(days=1)
    start_date = timezone.make_aware(
        datetime.datetime.combine(earliest_date, datetime.datetime.min.time()),
        timezone.get_default_timezone()
    )
    datetime_start, _ = date_range_ops.get_datetime_range_for_date(start_date)
    _, datetime_end = date_range_ops.get_datetime_range_for_date(
        date_input - datetime.timedelta(days=1)
    )
    total_intake = date_range_ops.aggregate_calories_for_date_range(
        Intake, datetime_start, datetime_end
    )
    total_expenditure = (
            Expenditure.objects.filter(
                date__range=[start_date, date_input - datetime.timedelta(days=1)]
            ).aggregate(Sum("calories"))["calories__sum"]
            or 0
    )
    net_calorie_delta = total_expenditure - total_intake
    num_days = (date_input.date() - start_date.date()).days
    goal_calorie_total = goal_delta_per_day * num_days
    adjustment_needed = abs(goal_calorie_total) - net_calorie_delta
    user_profile.adjustment = adjustment_needed
    user_profile.save()
