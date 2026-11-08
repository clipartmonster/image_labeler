from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


def _backfill_training_result_pay(apps, schema_editor):
    """Copy per-session rate from the training assignment onto each attempt."""
    TrainingResult = apps.get_model("label_images", "TrainingResult")
    BatchAssignment = apps.get_model("label_images", "BatchAssignment")
    default_rate = Decimal(str(settings.LABELER_PAY_PER_BATCH))

    rate_by_user_feature = {}
    paid_by_user_feature = {}
    for a in BatchAssignment.objects.filter(is_training=True):
        key = (a.user_id, a.task_type, a.rule_index)
        rate_by_user_feature[key] = a.payment_amount or default_rate
        paid_by_user_feature[key] = bool(a.paid)

    for tr in TrainingResult.objects.all():
        key = (tr.user_id, tr.task_type, tr.rule_index)
        rate = rate_by_user_feature.get(key, default_rate)
        # Past pay lived on the assignment. If that row was already marked paid,
        # treat existing attempts as settled so we don't suddenly owe retries.
        already_paid = paid_by_user_feature.get(key, False)
        TrainingResult.objects.filter(pk=tr.pk).update(
            payment_amount=rate,
            paid=already_paid,
        )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("label_images", "0020_training_pass_gate"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainingresult",
            name="payment_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name="trainingresult",
            name="paid",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(_backfill_training_result_pay, _noop_reverse),
    ]
