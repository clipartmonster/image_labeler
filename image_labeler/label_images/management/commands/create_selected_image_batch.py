"""Create an internal selected-image review batch (default: 10×10 grid)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from label_images.models import SelectedImage, SelectedImageBatch
from label_images.preset_sampling import PRESETS, sample_preset_assets


class Command(BaseCommand):
    help = "Sample images into an internal SelectedImageBatch for the review page."

    def add_arguments(self, parser):
        parser.add_argument("--batch-number", type=int, default=1)
        parser.add_argument("--sample-size", type=int, default=100)
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional seed for reproducible candidate windows.",
        )
        parser.add_argument(
            "--preset",
            choices=sorted(PRESETS.keys()),
            default="sketch_fill_v2_low_density",
            help="Filter preset for the review sample.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace an existing batch with this batch_number.",
        )

    def handle(self, *args, **options):
        batch_number = options["batch_number"]
        sample_size = options["sample_size"]
        seed = options["seed"]
        replace = options["replace"]
        preset_name = options["preset"]
        preset = PRESETS[preset_name]

        existing = SelectedImageBatch.objects.filter(batch_number=batch_number).first()
        if existing and not replace:
            raise CommandError(
                f"Batch {batch_number} already exists (id={existing.id}). "
                "Pass --replace to rebuild it."
            )

        self.stdout.write(f"Sampling {sample_size} with preset={preset_name}...")
        selected = sample_preset_assets(preset, sample_size, seed=seed)

        sample_n = len(selected)
        if sample_n == 0:
            self.stderr.write("No assets matched the filters.")
            return

        with transaction.atomic():
            if existing:
                existing.images.all().delete()
                existing.delete()

            batch = SelectedImageBatch.objects.create(
                batch_number=batch_number,
                title=preset["title"],
                filters=preset["filters"],
                sample_size=sample_n,
                pool_size=sample_n,
            )
            SelectedImage.objects.bulk_create(
                [
                    SelectedImage(
                        batch=batch,
                        asset_id=item["asset_id"],
                        image_link=item["image_link"],
                        position=i,
                    )
                    for i, item in enumerate(selected)
                ]
            )

        seed_note = f"seed={seed}" if seed is not None else "random-windows"
        self.stdout.write(
            self.style.SUCCESS(
                f"Created selected-image batch {batch_number} ({preset_name}): "
                f"{sample_n} images ({seed_note}). "
                f"Open /label_images/view_selected_images/?batch={batch_number}"
            )
        )
