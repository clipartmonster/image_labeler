"""Consolidate labeled line_width_type rule 2 assets into the first large_sub_batches.

This command moves all labeled assets to the beginning large_sub_batches (1, 2, 3, etc.),
filling each to 100 assets before moving to the next. Unlabeled assets are moved to
higher numbered large_sub_batches.

Usage:
    python manage.py consolidate_labeled_lw2          # dry-run (default)
    python manage.py consolidate_labeled_lw2 --apply   # actually update the DB
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from labeling_api.models import label_data_selected_assets_new, line_width_sample_table


BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Consolidate labeled assets into first large_sub_batches for line_width_type rule 2"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes (default is dry-run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        
        # Get all line_width_type rule 2 assets
        all_assets = list(
            label_data_selected_assets_new.objects
            .filter(task_type="line_width_type", rule_index=2)
            .order_by("batch_id", "asset_id")
            .values("asset_id", "batch_id", "large_sub_batch")
        )
        
        if not all_assets:
            self.stdout.write("No line_width_type rule 2 assets found.")
            return
        
        # Get all labeled assets
        labeled_asset_ids = set(
            line_width_sample_table.objects
            .values_list("asset_id", flat=True)
            .distinct()
        )
        
        self.stdout.write(f"Total assets: {len(all_assets)}")
        self.stdout.write(f"Labeled assets: {len(labeled_asset_ids)}\n")
        
        # Group by batch_id
        assets_by_batch = {}
        for asset in all_assets:
            batch_id = asset["batch_id"]
            if batch_id not in assets_by_batch:
                assets_by_batch[batch_id] = {"labeled": [], "unlabeled": []}
            
            if asset["asset_id"] in labeled_asset_ids:
                assets_by_batch[batch_id]["labeled"].append(asset["asset_id"])
            else:
                assets_by_batch[batch_id]["unlabeled"].append(asset["asset_id"])
        
        # Process each batch_id
        for batch_id in sorted(assets_by_batch.keys()):
            labeled = assets_by_batch[batch_id]["labeled"]
            unlabeled = assets_by_batch[batch_id]["unlabeled"]
            
            self.stdout.write(f"\nBatch {batch_id}:")
            self.stdout.write(f"  Labeled: {len(labeled)} assets")
            self.stdout.write(f"  Unlabeled: {len(unlabeled)} assets")
            
            # Calculate how many large_sub_batches needed for labeled assets
            labeled_sub_batches_needed = (len(labeled) + BATCH_SIZE - 1) // BATCH_SIZE if labeled else 0
            
            self.stdout.write(
                f"  Will use large_sub_batches 1-{labeled_sub_batches_needed} for labeled assets"
            )
            
            # Reorganize labeled assets into first N large_sub_batches
            updates = []
            current_sub_batch = 1
            
            for i in range(0, len(labeled), BATCH_SIZE):
                chunk = labeled[i:i + BATCH_SIZE]
                self.stdout.write(
                    f"    → large_sub_batch {current_sub_batch}: {len(chunk)} labeled assets"
                )
                
                if apply:
                    label_data_selected_assets_new.objects.filter(
                        asset_id__in=chunk
                    ).update(
                        large_sub_batch=current_sub_batch
                    )
                
                current_sub_batch += 1
            
            # Reorganize unlabeled assets into remaining large_sub_batches
            for i in range(0, len(unlabeled), BATCH_SIZE):
                chunk = unlabeled[i:i + BATCH_SIZE]
                self.stdout.write(
                    f"    → large_sub_batch {current_sub_batch}: {len(chunk)} unlabeled assets"
                )
                
                if apply:
                    label_data_selected_assets_new.objects.filter(
                        asset_id__in=chunk
                    ).update(
                        large_sub_batch=current_sub_batch
                    )
                
                current_sub_batch += 1
            
            total_sub_batches = current_sub_batch - 1
            self.stdout.write(f"  Total large_sub_batches: {total_sub_batches}")

        if apply:
            self.stdout.write(self.style.SUCCESS("\nDone — changes applied."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nDry run — no changes made. Re-run with --apply to commit."
                )
            )
