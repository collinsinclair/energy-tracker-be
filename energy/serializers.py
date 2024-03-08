from rest_framework import serializers

from .models import CalorieExpenditure, Food, Weight


class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = "__all__"


class CalorieExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalorieExpenditure
        fields = "__all__"


class WeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weight
        fields = "__all__"
