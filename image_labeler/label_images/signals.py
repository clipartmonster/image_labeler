import logging
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

TRAINING_ASSET_COUNT = 150


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Auto-create a UserProfile with must_change_password=True for new users."""
    if not created or instance.is_superuser:
        return
    from .models import UserProfile
    UserProfile.objects.get_or_create(
        user=instance,
        defaults={"must_change_password": True},
    )


@receiver(post_save, sender=User)
def auto_assign_training_batches(sender, instance, created, **kwargs):
    """When a new labeler is created, build training batches from reconciled assets."""
    if not created:
        return
    if not instance.is_staff or instance.is_superuser:
        return

    try:
        _assign_training_batches(instance)
    except Exception:
        logger.exception("Failed to auto-assign training batches for %s", instance.username)


def _assign_training_batches(user):
    from labeling_api.models import (
        labelling_rules, assets_w_rule_labels, label_data_selected_assets_new,
    )
    from .models import BatchAssignment, TrainingBatchAsset

    features = list(set(
        labelling_rules.objects.exclude(task_type="color_type")
        .values_list("task_type", "rule_index")
    ))

    deadline = timezone.now() + timedelta(days=30)

    for task_type, rule_index in features:
        reconciled = list(
            assets_w_rule_labels.objects
            .filter(task_type=task_type, rule_index=rule_index, percent_agree__gte=0.9)
            .values_list("asset_id", "label")
        )

        if len(reconciled) < 10:
            continue

        sampled = random.sample(reconciled, min(TRAINING_ASSET_COUNT, len(reconciled)))
        sampled_ids = [a[0] for a in sampled]
        label_map = {a[0]: a[1] for a in sampled}

        image_links = dict(
            label_data_selected_assets_new.objects
            .filter(asset_id__in=sampled_ids)
            .values_list("asset_id", "image_link")
        )

        assets_with_links = [
            (aid, image_links[aid], label_map[aid])
            for aid in sampled_ids if aid in image_links
        ]

        if not assets_with_links:
            continue

        # Use batch_id=0, large_sub_batch=0 as a sentinel for training batches
        assignment, _ = BatchAssignment.objects.get_or_create(
            user=user,
            task_type=task_type,
            rule_index=rule_index,
            batch_id=0,
            large_sub_batch=0,
            defaults={
                "payment_amount": 0,
                "deadline": deadline,
                "is_training": True,
            },
        )

        TrainingBatchAsset.objects.bulk_create(
            [
                TrainingBatchAsset(
                    assignment=assignment,
                    asset_id=aid,
                    image_link=link,
                    correct_label=label,
                )
                for aid, link, label in assets_with_links
            ],
            ignore_conflicts=True,
        )

        logger.info(
            "Created training batch for %s: %s/rule_%d with %d assets",
            user.username, task_type, rule_index, len(assets_with_links),
        )
