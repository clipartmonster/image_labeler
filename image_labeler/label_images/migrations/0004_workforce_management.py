"""Add workforce management models and fields.

- BatchAssignment: deadline_warning_severity, num_labelers_target, gold_percentage
- GoldStandardLabel, AdjudicationDecision (new models)
- Backfill: set User.is_staff=True for superusers, False for everyone else
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_is_staff(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(is_superuser=True).update(is_staff=True)
    User.objects.filter(is_superuser=False).update(is_staff=False)


def reverse_is_staff(apps, schema_editor):
    pass  # no-op; original values unknown


class Migration(migrations.Migration):

    dependencies = [
        ("label_images", "0003_userprofile_must_change_password"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- BatchAssignment new fields ---
        migrations.AddField(
            model_name="batchassignment",
            name="deadline_warning_severity",
            field=models.CharField(
                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                default="medium",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="batchassignment",
            name="num_labelers_target",
            field=models.PositiveIntegerField(default=2),
        ),
        migrations.AddField(
            model_name="batchassignment",
            name="gold_percentage",
            field=models.FloatField(
                default=5.0,
                help_text="Percent of gold-standard assets to inject when serving this batch.",
            ),
        ),

        # --- GoldStandardLabel ---
        migrations.CreateModel(
            name="GoldStandardLabel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.BigIntegerField()),
                ("task_type", models.CharField(max_length=100)),
                ("rule_index", models.IntegerField()),
                ("correct_response", models.CharField(max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("asset_id", "task_type", "rule_index")},
                "indexes": [
                    models.Index(fields=["task_type", "rule_index"], name="label_ima_task_ty_gold_idx"),
                ],
            },
        ),

        # --- AdjudicationDecision ---
        migrations.CreateModel(
            name="AdjudicationDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.BigIntegerField()),
                ("task_type", models.CharField(max_length=100)),
                ("rule_index", models.IntegerField()),
                ("decision", models.CharField(max_length=10)),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("decided_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="adjudications",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "unique_together": {("asset_id", "task_type", "rule_index")},
            },
        ),

        # --- Backfill is_staff ---
        migrations.RunPython(backfill_is_staff, reverse_is_staff),
    ]
