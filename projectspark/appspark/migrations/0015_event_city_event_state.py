# Generated by Django 5.0.1 on 2024-02-16 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0014_event_delete_city_delete_state_company_profile_pic_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='city',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='event',
            name='state',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
    ]