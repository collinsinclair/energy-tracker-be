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
            - user_profile.previous_day_surplus_calories
        )
        return adjusted_goal


date_range_ops = DateRangeOperationsMixin()


def update_previous_day_surplus_calories(date):
    Intake = apps.get_model("energy", "Intake")
    Expenditure = apps.get_model("energy", "Expenditure")
    UserProfile = apps.get_model("energy", "UserProfile")
    three_days_prior = date - timedelta(days=3)
    datetime_start, _ = date_range_ops.get_datetime_range_for_date(three_days_prior)
    _, datetime_end = date_range_ops.get_datetime_range_for_date(
        date - timedelta(days=1)
    )
    total_intake = date_range_ops.aggregate_calories_for_date_range(
        Intake, datetime_start, datetime_end
    )
    total_expenditure = (
        Expenditure.objects.filter(
            date__range=[three_days_prior, date - timedelta(days=1)]
        ).aggregate(Sum("calories"))["calories__sum"]
        or 0
    )
    user_profile = UserProfile.objects.first()
    goal_delta = user_profile.goal_daily_calorie_delta
    remaining_calories = total_expenditure - total_intake
    daily_goal_delta = goal_delta * 3
    if daily_goal_delta < 0:
        unmet_deficit = abs(daily_goal_delta) - remaining_calories
        if unmet_deficit > 0:
            user_profile.previous_day_surplus_calories = unmet_deficit
        else:
            user_profile.previous_day_surplus_calories = 0
    else:
        if remaining_calories < daily_goal_delta:
            user_profile.previous_day_surplus_calories = (
                daily_goal_delta - remaining_calories
            )
        else:
            user_profile.previous_day_surplus_calories = 0
    user_profile.save()
