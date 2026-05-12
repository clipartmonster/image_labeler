import logging
from datetime import timedelta
from collections import defaultdict

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

BATCHES_PER_FEATURE = 2


@receiver(post_save, sender=User)
def auto_assign_test_batches(sender, instance, created, **kwargs):
    """When a new labeler is created, assign 2 existing sub-batches per feature.

    Picks sub-batches with the highest proportion of reconciled assets
    (from assets_w_rule_labels with percent_agree >= 0.9).
    """
    if not created:
        return
    if not instance.is_staff or instance.is_superuser:
        return

    try:
        _assign_test_batches(instance)
    except Exception:
        logger.exception("Failed to auto-assign test batches for %s", instance.username)


def _assign_test_batches(user):
    from labeling_api.models import (
        labelling_rules, label_data_selected_assets_new, assets_w_rule_labels,
    )
    from .models import BatchAssignment

    features = list(
        labelling_rules.objects.exclude(task_type="color_type")
        .values_list("task_type", "rule_index")
        .distinct()
    )

    for task_type, rule_index in features:
        reconciled_ids = set(
            assets_w_rule_labels.objects
            .filter(task_type=task_type, rule_index=rule_index, percent_agree__gte=0.9)
            .values_list("asset_id", flat=True)[:5000]
        )

        if not reconciled_ids:
            continue

        sb_assets = defaultdict(set)
        for row in (
            label_data_selected_assets_new.objects
            .filter(task_type=task_type, rule_index=rule_index)
            .values_list("batch_id", "large_sub_batch", "asset_id")
        ):
            sb_assets[(row[0], row[1])].add(row[2])

        scored = []
        for (bid, lsb), asset_ids in sb_assets.items():
            overlap = len(asset_ids & reconciled_ids)
            total = len(asset_ids)
            if overlap > 0:
                scored.append((overlap, total, bid, lsb))

        scored.sort(key=lambda x: (-x[0], x[1]))

        deadline = timezone.now() + timedelta(days=30)
        for _, _, bid, lsb in scored[:BATCHES_PER_FEATURE]:
            BatchAssignment.objects.get_or_create(
                user=user,
                task_type=task_type,
                rule_index=rule_index,
                batch_id=bid,
                large_sub_batch=lsb,
                defaults={
                    "payment_amount": 0,
                    "deadline": deadline,
                },
            )
