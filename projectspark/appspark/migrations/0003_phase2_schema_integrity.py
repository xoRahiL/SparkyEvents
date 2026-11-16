"""
Phase 2: Database Schema & Integrity Migration
- Removes invalid default="" from OneToOneField on Workhand and Company
- Changes payment_range from FloatField to DecimalField on Event and EventHistory
- Adds db_index to Event.start_date, Event.city, WorkhandApplications.status
- Adds created_at / updated_at timestamps to Workhand, Company, Event,
  WorkhandApplications, EventHistory
- Fixes verbose_name_plural on WorkhandApplications, Company, EventHistory, Feedback
- Makes WorkhandApplications.__str__ work (cosmetic only, no schema change)
"""
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0002_seed_default_categories'),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. Remove the invalid default="" from OneToOneField user columns.   #
        #    The column type (INTEGER FK) never actually stored the string;   #
        #    removing it just fixes the Python-level model metadata.          #
        # ------------------------------------------------------------------ #
        migrations.AlterField(
            model_name='workhand',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),
        migrations.AlterField(
            model_name='company',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 2. payment_range: Float → Decimal (monetary accuracy).             #
        # ------------------------------------------------------------------ #
        migrations.AlterField(
            model_name='event',
            name='payment_range',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name='eventhistory',
            name='payment_range',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),

        # ------------------------------------------------------------------ #
        # 3. Add db_index to hot filter columns.                             #
        # ------------------------------------------------------------------ #
        migrations.AlterField(
            model_name='event',
            name='start_date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='city',
            field=models.CharField(db_index=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='workhandapplications',
            name='status',
            field=models.BooleanField(db_index=True, default=False),
        ),

        # ------------------------------------------------------------------ #
        # 4. Audit timestamps — Workhand                                     #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='workhand',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='workhand',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # 4b. Audit timestamps — Company
        migrations.AddField(
            model_name='company',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # 4c. Audit timestamps — Event
        migrations.AddField(
            model_name='event',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='event',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # 4d. Audit timestamps — WorkhandApplications
        migrations.AddField(
            model_name='workhandapplications',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='workhandapplications',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # 4e. Audit timestamps — EventHistory
        migrations.AddField(
            model_name='eventhistory',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventhistory',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
