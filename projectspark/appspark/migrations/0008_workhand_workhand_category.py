# Generated by Django 5.0.1 on 2024-02-13 11:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0007_remove_workhand_workhand_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='workhand',
            name='workhand_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhandcategory'),
        ),
    ]