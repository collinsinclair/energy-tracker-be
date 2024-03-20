# energy/models.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from energy.utils import update_remaining_calories_adjustment


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal_weight = models.IntegerField(default=-1)
    goal_daily_calorie_delta = models.IntegerField(default=0)
    adjustment = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username


# Signal to create or update user profile
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        profile, was_created = UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "goal_weight": -1,
                "goal_daily_calorie_delta": 0,
                "previous_day_surplus_calories": 0,
            },
        )


class Intake(models.Model):
    label = models.CharField(max_length=100)
    calories = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.label} ({self.calories} cal)"

    class Meta:
        verbose_name_plural = "Intakes"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        date = timezone.localtime(self.timestamp).date()
        update_remaining_calories_adjustment(date)


class Expenditure(models.Model):
    calories = models.IntegerField()
    date = models.DateField(unique=True)

    def __str__(self):
        formatted_date = self.date.strftime("%b %-d")
        return f"{formatted_date} - {self.calories} cal"

    class Meta:
        verbose_name_plural = "Expenditures"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_remaining_calories_adjustment(self.date)


@receiver(post_save, sender=Intake)
@receiver(post_delete, sender=Intake)
@receiver(post_save, sender=Expenditure)
@receiver(post_delete, sender=Expenditure)
def update_surplus_calories(sender, instance, **kwargs):
    if hasattr(instance, "date"):
        update_date = instance.date
    else:
        update_date = timezone.localtime(instance.timestamp).date()
    update_remaining_calories_adjustment(update_date)


class Weight(models.Model):
    weight = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.weight} lbs"

    class Meta:
        verbose_name_plural = "Weights"
