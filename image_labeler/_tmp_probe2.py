import sys
from django.conf import settings
from django.db import connections

db = "prod" if "prod" in settings.DATABASES else "default"
print("db", db, flush=True)
with connections[db].cursor() as cur:
    cur.execute(
        """
        SELECT DISTINCT model_version
        FROM model_predictions.rule_labels
        WHERE task_type = 'color_fill_type' AND rule_index = 1
        ORDER BY 1
        LIMIT 20
        """
    )
    print("paint_versions", [r[0] for r in cur.fetchall()], flush=True)
    cur.execute(
        """
        SELECT DISTINCT model_version
        FROM model_predictions.rule_labels
        WHERE task_type = 'color_fill_type' AND rule_index = 2
        ORDER BY 1
        LIMIT 20
        """
    )
    print("depth_versions", [r[0] for r in cur.fetchall()], flush=True)
    cur.execute("SELECT COUNT(*) FROM model_predictions.stage_multi_color")
    print("multi_count", cur.fetchone()[0], flush=True)
print("ok", flush=True)
