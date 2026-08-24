"""Fill the model coverage cache so the page never has to compute on demand.

Every count reads ``model_predictions.rule_labels`` (113M rows), which takes a few
seconds each, and the S3 asset count takes about two and a half minutes. Run this on
a schedule -- after the prediction pipeline finishes is the useful moment -- and the
page only ever reads cached numbers.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Precompute the model coverage counts shown on the Model Coverage page."

    def add_arguments(self, parser):
        parser.add_argument(
            "--budget", type=float, default=1800,
            help="Seconds to spend before leaving the rest for the next run.",
        )
        parser.add_argument(
            "--refresh", action="store_true",
            help="Discard the cached counts first instead of filling in the gaps.",
        )

    def handle(self, *args, **options):
        # Imported here so the command doesn't drag the API views in at startup.
        from labeling_api.views import get_model_coverage
        from rest_framework.test import APIRequestFactory
        from django.conf import settings

        request = APIRequestFactory().post(
            "/get_model_coverage/",
            {"budget_seconds": options["budget"],
             "refresh": "1" if options["refresh"] else ""},
            format="json",
            HTTP_AUTHORIZATION=settings.API_ACCESS_KEY,
        )
        response = get_model_coverage(request)
        payload = response.data if hasattr(response, "data") else {}
        if not payload:
            import json
            payload = json.loads(response.content)

        took = payload.get("took_seconds")
        pending = payload.get("pending", 0)
        root = payload.get("root_assets")

        for stage in payload.get("stages", []):
            self.stdout.write(self.style.HTTP_INFO(f"\n{stage['label']}"))
            for model in stage["models"]:
                name = f"{model['task_type']}/{model['rule_index']}"
                if model["covered"] is None:
                    self.stdout.write(f"  {name:<32} not counted yet")
                    continue
                percent = f"{model['percent']}%" if model["percent"] is not None else "-"
                self.stdout.write(
                    f"  {name:<32}{model['covered']:>12,} covered  {percent:>7}"
                )

        self.stdout.write("")
        self.stdout.write(
            f"S3 assets: {root:,}" if root else "S3 assets: not counted yet"
        )
        if pending:
            self.stdout.write(self.style.WARNING(
                f"{pending} count(s) still outstanding after {took}s; "
                "run again to finish them."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f"All counts cached in {took}s."))
