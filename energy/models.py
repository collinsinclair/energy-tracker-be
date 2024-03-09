from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal_weight = models.IntegerField(default=-1)
    goal_daily_calorie_delta = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username


# Signal to create/update user profile
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()


class Intake(models.Model):
    label = models.CharField(max_length=100)
    calories = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.calories} cal)"

    class Meta:
        verbose_name_plural = "Intakes"


class Expenditure(models.Model):
    calories = models.IntegerField()
    date = models.DateField(unique=True)

    def __str__(self):
        formatted_date = self.date.strftime("%b %-d")
        return f"{formatted_date} - {self.calories} cal"

    class Meta:
        verbose_name_plural = "Expenditures"


class Weight(models.Model):
    weight = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.weight} lbs"

    class Meta:
        verbose_name_plural = "Weights"
