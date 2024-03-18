# energy/utils.py
import datetime

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


def update_previous_day_surplus_calories(date):
    from datetime import timedelta
    from django.apps import apps

    print(f"Starting update for date: {date}")

    # Assuming DateRangeOperationsMixin is defined elsewhere and available
    date_range_ops = DateRangeOperationsMixin()

    # Models retrieval
    Intake = apps.get_model("energy", "Intake")
    Expenditure = apps.get_model("energy", "Expenditure")
    UserProfile = apps.get_model("energy", "UserProfile")
    print("Models loaded successfully.")

    # Calculate the date range for the previous day
    previous_day = date - timedelta(days=1)
    datetime_start, datetime_end = date_range_ops.get_datetime_range_for_date(
        previous_day
    )
    print(
        f"Previous day: {previous_day}, datetime range: {datetime_start} to {datetime_end}"
    )

    # Aggregate calories for the date range
    total_intake = date_range_ops.aggregate_calories_for_date_range(
        Intake, datetime_start, datetime_end
    )
    print(f"Total intake: {total_intake}")

    expenditure_record = Expenditure.objects.filter(date=previous_day).first()
    total_expenditure = expenditure_record.calories if expenditure_record else 0
    print(f"Total expenditure: {total_expenditure}")

    # Retrieve the user profile and goal
    user_profile = UserProfile.objects.first()
    goal_delta = user_profile.goal_daily_calorie_delta
    print(f"User goal daily calorie delta: {goal_delta}")

    # Calculate remaining calories considering the goal
    remaining_calories = (
        total_expenditure - total_intake
    )  # Actual balance without considering the goal
    print(f"Remaining calories (before goal consideration): {remaining_calories}")

    if goal_delta < 0:  # Goal is a deficit
        print("Goal is a deficit.")
        # Correctly calculate the unmet deficit portion
        unmet_deficit = abs(goal_delta) - remaining_calories
        if unmet_deficit > 0:
            user_profile.previous_day_surplus_calories = unmet_deficit
            print(
                f"Unmet deficit portion correctly recorded: {user_profile.previous_day_surplus_calories}"
            )
        else:
            user_profile.previous_day_surplus_calories = 0
            print("No unmet deficit. previous_day_surplus_calories set to 0.")
    else:  # Goal is a surplus
        # If actual surplus is less than goal surplus, record the unmet portion
        if remaining_calories < goal_delta:
            user_profile.previous_day_surplus_calories = goal_delta - remaining_calories
            print(
                f"Unmet surplus portion recorded: {user_profile.previous_day_surplus_calories}"
            )
        else:
            user_profile.previous_day_surplus_calories = 0
            print("No unmet surplus. previous_day_surplus_calories set to 0.")

    # Save the updated profile
    user_profile.save()
    print("User profile updated and saved.")
