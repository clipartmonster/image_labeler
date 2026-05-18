"""Split existing line_width_type rule 2 large_sub_batches into chunks of 100.

Usage:
    python manage.py split_lw2_subbatches          # dry-run (default)
    python manage.py split_lw2_subbatches --apply   # actually update the DB
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from labeling_api.models import label_data_selected_assets_new


CHUNK_SIZE = 100


class Command(BaseCommand):
    help = "Re-chunk line_width_type rule 2 sub-batches from 500 → 100"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes (default is dry-run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        qs = label_data_selected_assets_new.objects.filter(
            task_type="line_width_type", rule_index=2
        )

        batches = (
            qs.values("batch_id", "large_sub_batch")
            .annotate(cnt=Count("asset_id"))
            .order_by("batch_id", "large_sub_batch")
        )

        if not batches:
            self.stdout.write("No line_width_type rule 2 sub-batches found.")
            return

        for b in batches:
            bid = b["batch_id"]
            lsb = b["large_sub_batch"]
            cnt = b["cnt"]

            if cnt <= CHUNK_SIZE:
                self.stdout.write(
                    f"  batch {bid} lsb {lsb}: {cnt} assets — already ≤{CHUNK_SIZE}, skipping"
                )
                continue

            self.stdout.write(
                f"  batch {bid} lsb {lsb}: {cnt} assets — splitting into chunks of {CHUNK_SIZE}"
            )

            max_lsb = (
                label_data_selected_assets_new.objects.filter(
                    task_type="line_width_type", rule_index=2, batch_id=bid
                )
                .order_by("-large_sub_batch")
                .values_list("large_sub_batch", flat=True)
                .first()
            ) or 0

            assets = list(
                qs.filter(batch_id=bid, large_sub_batch=lsb)
                .order_by("asset_id")
                .values_list("asset_id", flat=True)
            )

            # First chunk keeps the original lsb, remaining get new lsb numbers
            new_lsb = max_lsb
            for i in range(CHUNK_SIZE, len(assets), CHUNK_SIZE):
                new_lsb += 1
                chunk_ids = assets[i : i + CHUNK_SIZE]
                self.stdout.write(
                    f"    → {len(chunk_ids)} assets → new lsb {new_lsb}"
                )
                if apply:
                    qs.filter(asset_id__in=chunk_ids).update(large_sub_batch=new_lsb)

            kept = min(CHUNK_SIZE, len(assets))
            self.stdout.write(f"    → {kept} assets remain in original lsb {lsb}")

        if apply:
            self.stdout.write(self.style.SUCCESS("\nDone — changes applied."))
        else:
            self.stdout.write(
                self.style.WARNING("\nDry run — no changes made. Re-run with --apply to commit.")
            )
