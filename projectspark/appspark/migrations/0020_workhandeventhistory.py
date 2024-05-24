# Generated by Django 5.0.1 on 2024-02-20 15:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0019_rename_by_workhand_workhandapplications_workhand'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkhandEventHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_name', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('workhand_needed', models.IntegerField()),
                ('payment_range', models.FloatField()),
                ('address', models.TextField()),
                ('state', models.CharField(max_length=50)),
                ('city', models.CharField(max_length=50)),
                ('company_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.company')),
                ('event_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.eventscategory')),
                ('workhand_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhandcategory')),
            ],
        ),
    ]