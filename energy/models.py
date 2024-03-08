from django.db import models


class Food(models.Model):
    label = models.CharField(max_length=100)
    calories = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.calories} cal)"

    class Meta:
        verbose_name_plural = "Foods"


class CalorieExpenditure(models.Model):
    calories = models.IntegerField()
    date = models.DateField(unique=True)

    def __str__(self):
        formatted_date = self.date.strftime("%b %-d")
        return f"{formatted_date} - {self.calories} cal"

    class Meta:
        verbose_name_plural = "Calorie Expenditures"


class Weight(models.Model):
    weight = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.weight} lbs"

    class Meta:
        verbose_name_plural = "Weights"
