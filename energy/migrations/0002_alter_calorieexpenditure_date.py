# Generated by Django 5.0.3 on 2024-03-08 20:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("energy", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calorieexpenditure",
            name="date",
            field=models.DateField(unique=True),
        ),
    ]
