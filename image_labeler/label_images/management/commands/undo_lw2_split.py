"""Undo the create_lw2_batches command by restoring original batch structure.

This command restores line_width_type rule 2 assets back to batch_id=1
and reconstructs the original large_sub_batch values.

Usage:
    python manage.py undo_lw2_split          # dry-run (default)
    python manage.py undo_lw2_split --apply   # actually update the DB
"""

from django.core.management.base import BaseCommand
from django.db.models import Min

from labeling_api.models import label_data_selected_assets_new


class Command(BaseCommand):
    help = "Undo create_lw2_batches by restoring batch_id=1 and original large_sub_batch"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes (default is dry-run).",
        )
        parser.add_argument(
            "--target-batch",
            type=int,
            default=1,
            help="Target batch_id to restore to (default: 1)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        target_batch = options["target_batch"]
        
        # Get all line_width_type rule 2 assets that were modified
        # These will all have large_sub_batch=1 after the incorrect split
        modified_batches = (
            label_data_selected_assets_new.objects
            .filter(
                task_type="line_width_type",
                rule_index=2,
                large_sub_batch=1
            )
            .exclude(batch_id=target_batch)
            .values("batch_id")
            .order_by("batch_id")
            .distinct()
        )
        
        batch_ids = [b["batch_id"] for b in modified_batches]
        
        if not batch_ids:
            self.stdout.write("No modified batches found to undo.")
            return
        
        self.stdout.write(
            f"Found {len(batch_ids)} batches to restore (batch_ids: {min(batch_ids)} to {max(batch_ids)})"
        )
        self.stdout.write(f"Will restore to batch_id={target_batch}\n")
        
        # Group consecutive pairs of batch_ids (they were split from one large_sub_batch)
        restored_count = 0
        next_sub_batch = 1
        
        # Process in pairs
        for i in range(0, len(batch_ids), 2):
            if i + 1 < len(batch_ids):
                # Pair of batch_ids
                batch_id_1 = batch_ids[i]
                batch_id_2 = batch_ids[i + 1]
                
                # Get assets from both batches
                assets_1 = list(
                    label_data_selected_assets_new.objects
                    .filter(
                        task_type="line_width_type",
                        rule_index=2,
                        batch_id=batch_id_1
                    )
                    .order_by("asset_id")
                    .values_list("asset_id", flat=True)
                )
                
                assets_2 = list(
                    label_data_selected_assets_new.objects
                    .filter(
                        task_type="line_width_type",
                        rule_index=2,
                        batch_id=batch_id_2
                    )
                    .order_by("asset_id")
                    .values_list("asset_id", flat=True)
                )
                
                total_assets = len(assets_1) + len(assets_2)
                
                self.stdout.write(
                    f"Restoring batches {batch_id_1}, {batch_id_2} "
                    f"→ batch {target_batch} / large_sub_batch {next_sub_batch} "
                    f"({total_assets} assets)"
                )
                
                if apply:
                    # Restore both halves to the same large_sub_batch
                    label_data_selected_assets_new.objects.filter(
                        asset_id__in=assets_1 + assets_2
                    ).update(
                        batch_id=target_batch,
                        large_sub_batch=next_sub_batch
                    )
                
                restored_count += 1
                next_sub_batch += 1
            else:
                # Odd one out (shouldn't happen but handle it)
                batch_id_1 = batch_ids[i]
                assets = list(
                    label_data_selected_assets_new.objects
                    .filter(
                        task_type="line_width_type",
                        rule_index=2,
                        batch_id=batch_id_1
                    )
                    .values_list("asset_id", flat=True)
                )
                
                self.stdout.write(
                    f"Restoring batch {batch_id_1} "
                    f"→ batch {target_batch} / large_sub_batch {next_sub_batch} "
                    f"({len(assets)} assets)"
                )
                
                if apply:
                    label_data_selected_assets_new.objects.filter(
                        asset_id__in=assets
                    ).update(
                        batch_id=target_batch,
                        large_sub_batch=next_sub_batch
                    )
                
                restored_count += 1
                next_sub_batch += 1
        
        self.stdout.write(f"\nRestored {restored_count} large_sub_batches")

        if apply:
            self.stdout.write(self.style.SUCCESS("\nDone — changes applied."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nDry run — no changes made. Re-run with --apply to commit."
                )
            )
