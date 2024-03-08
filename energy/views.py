from rest_framework import viewsets

from .models import CalorieExpenditure, Food, Weight
from .serializers import CalorieExpenditureSerializer, FoodSerializer, WeightSerializer


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.all()
    serializer_class = FoodSerializer


class CalorieExpenditureViewSet(viewsets.ModelViewSet):
    queryset = CalorieExpenditure.objects.all()
    serializer_class = CalorieExpenditureSerializer


class WeightViewSet(viewsets.ModelViewSet):
    queryset = Weight.objects.all()
    serializer_class = WeightSerializer
