"""Create an internal selected-image review batch (default: 10×10 grid)."""

from __future__ import annotations

import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, transaction

from label_images.models import SelectedImage, SelectedImageBatch


# Sketch Fill V2 has no dedicated model yet. Batch selection for that task used
# Color Fill / Sketch Elements (CF7) positives, so the same signal is the
# "Sketch Fill V2 candidate" filter here.
DEFAULT_FILTERS = [
    "Mono-color clip art (stage_mono_color)",
    "Sketch Fill V2 candidate: Sketch Elements CF7_0.01 = True",
    "Color pixel density ratio < 0.3 (CD1_0.01)",
    "S3 image available",
]


class Command(BaseCommand):
    help = "Sample images into an internal SelectedImageBatch for the review page."

    def add_arguments(self, parser):
        parser.add_argument("--batch-number", type=int, default=1)
        parser.add_argument("--sample-size", type=int, default=100)
        parser.add_argument("--seed", type=int, default=42)
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

        existing = SelectedImageBatch.objects.filter(batch_number=batch_number).first()
        if existing and not replace:
            self.stderr.write(
                f"Batch {batch_number} already exists (id={existing.id}). "
                "Pass --replace to rebuild it."
            )
            return

        db = "prod" if "prod" in settings.DATABASES else "default"
        with connections[db].cursor() as cur:
            cur.execute(
                """
                SELECT m.asset_id, a.image_link
                FROM model_predictions.stage_mono_color m
                JOIN model_predictions.color_pixel_density d
                  ON d.asset_id = m.asset_id
                JOIN model_predictions.rule_labels r
                  ON r.asset_id = m.asset_id
                JOIN content.assets a
                  ON a.asset_id = m.asset_id
                WHERE d.model_version = 'CD1_0.01'
                  AND d.ratio < 0.3
                  AND d.ratio = d.ratio
                  AND d.ratio <> 'Infinity'::float8
                  AND d.ratio <> '-Infinity'::float8
                  AND r.task_type = 'color_fill_type'
                  AND r.rule_index = 7
                  AND r.model_version = 'CF7_0.01'
                  AND r.label = 1
                  AND a.s3 = TRUE
                  AND a.image_link IS NOT NULL
                  AND a.image_link <> ''
                """
            )
            pool = [{"asset_id": row[0], "image_link": row[1]} for row in cur.fetchall()]

        pool_size = len(pool)
        if pool_size == 0:
            self.stderr.write("No assets matched the filters.")
            return

        rng = random.Random(seed)
        sample_n = min(sample_size, pool_size)
        selected = rng.sample(pool, sample_n)

        with transaction.atomic():
            if existing:
                existing.images.all().delete()
                existing.delete()

            batch = SelectedImageBatch.objects.create(
                batch_number=batch_number,
                title="Sketch Fill V2 candidates · mono-color · low density",
                filters=DEFAULT_FILTERS,
                sample_size=sample_n,
                pool_size=pool_size,
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Created selected-image batch {batch_number}: "
                f"{sample_n} of {pool_size} matching assets (seed={seed})."
            )
        )
