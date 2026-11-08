"""Sample filtered assets into label_data.selected_assets_new labeling queues."""

from __future__ import annotations

from datetime import date

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from label_images.preset_sampling import PRESETS, sample_preset_assets
from labeling_api.models import label_data_selected_assets_new


class Command(BaseCommand):
    help = (
        "Sample assets into selected_assets_new as large_sub_batches "
        "(labeling queue, not the review panel). Uses the same presets as "
        "create_selected_image_batch."
    )

    def add_arguments(self, parser):
        parser.add_argument("--task-type", default="color_fill_type")
        parser.add_argument("--rule-index", type=int, default=5)
        parser.add_argument("--batch-id", type=int, default=3)
        parser.add_argument(
            "--sub-batches",
            type=int,
            default=5,
            help="Number of large_sub_batches to create (default 5).",
        )
        parser.add_argument(
            "--sub-batch-size",
            type=int,
            default=50,
            help="Assets per large_sub_batch (default 50).",
        )
        parser.add_argument(
            "--preset",
            choices=sorted(PRESETS.keys()),
            default="cf5_multi_depth_yes_paint_no",
            help="Filter preset (same as create_selected_image_batch).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional seed for reproducible candidate windows.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing rows for this task/rule/batch_id before inserting.",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Keep existing rows; new large_sub_batches continue after the current max.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Sample and report only; do not write to selected_assets_new.",
        )
        parser.add_argument(
            "--verify-images",
            action="store_true",
            help="Only keep assets whose image_link loads as a real image.",
        )

    def handle(self, *args, **options):
        task_type = options["task_type"]
        rule_index = options["rule_index"]
        batch_id = options["batch_id"]
        sub_batches = options["sub_batches"]
        sub_batch_size = options["sub_batch_size"]
        preset_name = options["preset"]
        seed = options["seed"]
        replace = options["replace"]
        append = options["append"]
        dry_run = options["dry_run"]
        verify_images = options["verify_images"]
        preset = PRESETS[preset_name]

        if sub_batches < 1 or sub_batch_size < 1:
            raise CommandError("--sub-batches and --sub-batch-size must be >= 1")
        if replace and append:
            raise CommandError("Pass only one of --replace or --append")

        sample_size = sub_batches * sub_batch_size

        existing_qs = label_data_selected_assets_new.objects.filter(
            task_type=task_type, rule_index=rule_index, batch_id=batch_id
        )
        existing_count = existing_qs.count()
        if existing_count and not replace and not append and not dry_run:
            raise CommandError(
                f"{task_type} rule {rule_index} batch {batch_id} already has "
                f"{existing_count} assets. Pass --replace or --append."
            )

        if replace:
            labeled = existing_qs.filter(label_count__gt=0).count()
            if labeled:
                raise CommandError(
                    f"Refusing --replace: {labeled} assets in batch {batch_id} "
                    f"already have label_count > 0."
                )
            if not dry_run:
                deleted, _ = existing_qs.delete()
                self.stdout.write(
                    f"Removed {deleted} existing row(s) from batch {batch_id}."
                )

        exclude_qs = label_data_selected_assets_new.objects.filter(
            task_type=task_type, rule_index=rule_index
        )
        if replace:
            exclude_qs = exclude_qs.exclude(batch_id=batch_id)
        exclude_ids = set(exclude_qs.values_list("asset_id", flat=True))

        self.stdout.write(
            f"Sampling {sample_size} with preset={preset_name} "
            f"(excluding {len(exclude_ids)} already on {task_type}/rule {rule_index})..."
        )
        for line in preset.get("filters") or []:
            self.stdout.write(f"  - {line}")

        selected = sample_preset_assets(
            preset,
            sample_size,
            exclude_ids=exclude_ids,
            seed=seed,
            verify_images=verify_images,
        )

        sample_n = len(selected)
        if sample_n == 0:
            raise CommandError("No assets matched the filters.")
        if sample_n < sample_size:
            raise CommandError(
                f"Only {sample_n} assets available after exclusions; "
                f"need {sample_size}."
            )

        if append:
            max_lsb = (
                label_data_selected_assets_new.objects.filter(
                    task_type=task_type, rule_index=rule_index, batch_id=batch_id
                ).aggregate(m=Max("large_sub_batch"))["m"]
                or 0
            )
        else:
            max_lsb = 0
        start_lsb = max_lsb + 1
        end_lsb = max_lsb + sub_batches

        seed_note = f"seed={seed}" if seed is not None else "random-windows"
        self.stdout.write(
            f"Ready: {sample_n} assets -> {task_type} rule {rule_index} "
            f"batch {batch_id}, large_sub_batches {start_lsb}-{end_lsb} "
            f"({sub_batch_size} each, {seed_note})."
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no rows written."))
            return

        date_now = date.today()
        rows = [
            label_data_selected_assets_new(
                asset_id=asset["asset_id"],
                image_link=asset["image_link"],
                batch_id=batch_id,
                date_created=date_now,
                label_count=0,
                asset_type="undetermined",
                clip_art_type=0,
                count=0,
                line_width=0,
                color_depth=0,
                primary_color=0,
                sub_batch=(i // 5) + 1,
                large_sub_batch=(i // sub_batch_size) + start_lsb,
                color_type="undetermined",
                multi_element="undetermined",
                task_type=task_type,
                rule_index=rule_index,
            )
            for i, asset in enumerate(selected)
        ]

        with transaction.atomic():
            label_data_selected_assets_new.objects.bulk_create(rows, batch_size=500)

        cache.clear()
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(rows)} assets in {task_type} rule {rule_index} "
                f"batch {batch_id}, large_sub_batches {start_lsb}-{end_lsb}."
            )
        )
