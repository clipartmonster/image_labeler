"""Split existing line_width_type rule 2 large_sub_batches from 100 assets to 50 assets each.

This command takes existing large_sub_batches (100 assets each) and splits each one into
2 large_sub_batches of 50 assets each, keeping the same batch_id.
For example: batch_id=1 with 100 large_sub_batches → batch_id=1 with 200 large_sub_batches.

Usage:
    python manage.py create_lw2_batches          # dry-run (default)
    python manage.py create_lw2_batches --apply   # actually update the DB
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Max

from labeling_api.models import label_data_selected_assets_new, line_width_sample_table


NEW_BATCH_SIZE = 50


class Command(BaseCommand):
    help = "Split line_width_type rule 2 large_sub_batches: 100 assets → 2 sub_batches of 50 each"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes (default is dry-run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        
        # Get all existing batches with their asset counts
        batches = (
            label_data_selected_assets_new.objects
            .filter(task_type="line_width_type", rule_index=2)
            .values("batch_id", "large_sub_batch")
            .annotate(asset_count=Count("asset_id"))
            .order_by("batch_id", "large_sub_batch")
        )

        if not batches:
            self.stdout.write("No line_width_type rule 2 batches found.")
            return

        self.stdout.write(f"Found {len(batches)} existing large_sub_batch(es)")
        
        batches_created = 0
        assets_processed = 0
        batches_skipped = 0
        
        for batch_info in batches:
            old_batch_id = batch_info["batch_id"]
            old_sub_batch = batch_info["large_sub_batch"]
            asset_count = batch_info["asset_count"]
            
            self.stdout.write(
                f"\nProcessing batch {old_batch_id} / sub_batch {old_sub_batch}: "
                f"{asset_count} assets"
            )
            
            # Get all assets in this batch, ordered by asset_id
            assets = list(
                label_data_selected_assets_new.objects
                .filter(
                    task_type="line_width_type",
                    rule_index=2,
                    batch_id=old_batch_id,
                    large_sub_batch=old_sub_batch
                )
                .order_by("asset_id")
                .values_list("asset_id", flat=True)
            )
            
            # Check if any assets in this batch have labels
            labeled_assets = line_width_sample_table.objects.filter(
                asset_id__in=assets
            ).values_list("asset_id", flat=True).distinct()
            
            if labeled_assets:
                self.stdout.write(
                    f"  ⚠ Skipping — {len(labeled_assets)} asset(s) already have labels"
                )
                batches_skipped += 1
                continue
            
            # Get the highest large_sub_batch for this batch_id to create new ones
            max_sub_batch = (
                label_data_selected_assets_new.objects
                .filter(
                    task_type="line_width_type",
                    rule_index=2,
                    batch_id=old_batch_id
                )
                .aggregate(Max("large_sub_batch"))["large_sub_batch__max"]
            ) or 0
            
            # Split into chunks of NEW_BATCH_SIZE
            num_new_sub_batches = (len(assets) + NEW_BATCH_SIZE - 1) // NEW_BATCH_SIZE
            
            # First chunk keeps the original large_sub_batch, rest get new numbers
            for i in range(num_new_sub_batches):
                start_idx = i * NEW_BATCH_SIZE
                end_idx = start_idx + NEW_BATCH_SIZE
                chunk_assets = assets[start_idx:end_idx]
                
                if i == 0:
                    # Keep first chunk in original large_sub_batch
                    new_sub_batch = old_sub_batch
                else:
                    # Create new large_sub_batch numbers for remaining chunks
                    max_sub_batch += 1
                    new_sub_batch = max_sub_batch
                
                self.stdout.write(
                    f"  → batch {old_batch_id} / large_sub_batch {new_sub_batch}: "
                    f"{len(chunk_assets)} assets"
                )
                
                if apply:
                    label_data_selected_assets_new.objects.filter(
                        asset_id__in=chunk_assets
                    ).update(
                        large_sub_batch=new_sub_batch
                    )
                
                batches_created += 1
                assets_processed += len(chunk_assets)
        
        self.stdout.write(
            f"\nSummary:"
        )
        self.stdout.write(f"  New large_sub_batches created: {batches_created}")
        self.stdout.write(f"  Original large_sub_batches processed: {len(batches) - batches_skipped}")
        self.stdout.write(f"  Large_sub_batches skipped (already labeled): {batches_skipped}")
        self.stdout.write(f"  Total assets processed: {assets_processed}")

        if apply:
            self.stdout.write(
                self.style.SUCCESS("\nDone — changes applied.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nDry run — no changes made. Re-run with --apply to commit."
                )
            )
