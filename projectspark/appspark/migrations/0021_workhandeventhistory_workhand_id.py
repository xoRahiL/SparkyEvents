# Generated by Django 5.0.1 on 2024-02-20 15:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0020_workhandeventhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='workhandeventhistory',
            name='workhand_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhand'),
        ),
    ]
