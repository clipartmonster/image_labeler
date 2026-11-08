from django.conf import settings
from django.db import connections

db = "prod" if "prod" in settings.DATABASES else "default"
print("db", db, flush=True)
with connections[db].cursor() as cur:
    cur.execute(
        """
        SELECT model_version, label, COUNT(*)
        FROM model_predictions.rule_labels
        WHERE task_type='color_fill_type' AND rule_index=2 AND model_version LIKE 'CF2%%'
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )
    print("cf2", cur.fetchall(), flush=True)
    cur.execute(
        """
        SELECT model_version, label, COUNT(*)
        FROM model_predictions.rule_labels
        WHERE task_type='color_fill_type' AND rule_index=1 AND model_version LIKE 'CF1%%'
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )
    print("cf1", cur.fetchall(), flush=True)
print("done", flush=True)
