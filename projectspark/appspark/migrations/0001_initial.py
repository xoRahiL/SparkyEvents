import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventsCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='WorkhandCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_pic', models.ImageField(default='assets2/img/AnonymousPic.png', upload_to='')),
                ('company_name', models.CharField(blank=True, max_length=50, null=True)),
                ('contact', models.CharField(blank=True, max_length=20, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('state', models.CharField(blank=True, max_length=50, null=True)),
                ('city', models.CharField(blank=True, max_length=50, null=True)),
                ('user', models.OneToOneField(default='', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EventHistory',
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
            ],
        ),
        migrations.CreateModel(
            name='Event',
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
        migrations.CreateModel(
            name='Workhand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_pic', models.ImageField(default='assets2/img/AnonymousPic.png', upload_to='')),
                ('contact', models.CharField(blank=True, max_length=20, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('state', models.CharField(blank=True, max_length=50, null=True)),
                ('city', models.CharField(blank=True, max_length=50, null=True)),
                ('user', models.OneToOneField(default='', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('workhand_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhandcategory')),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_title', models.CharField(max_length=40)),
                ('feedback', models.TextField()),
                ('date', models.DateField()),
                ('company_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.company')),
                ('event_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.eventhistory')),
                ('workhand_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhand')),
            ],
        ),
        migrations.AddField(
            model_name='eventhistory',
            name='workhand_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhand'),
        ),
        migrations.CreateModel(
            name='WorkhandApplications',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.BooleanField(default=False)),
                ('event', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.event')),
                ('to_company', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.company')),
                ('workhand', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhand')),
            ],
        ),
        migrations.AddField(
            model_name='eventhistory',
            name='workhand_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appspark.workhandcategory'),
        ),
        migrations.AddConstraint(
            model_name='workhandapplications',
            constraint=models.UniqueConstraint(fields=('workhand', 'event'), name='unique_application_per_event'),
        ),
    ]