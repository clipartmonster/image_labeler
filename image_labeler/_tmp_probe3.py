from django.conf import settings
from django.db import connections

db = "prod" if "prod" in settings.DATABASES else "default"
print("db", db, flush=True)
with connections[db].cursor() as cur:
    # Prefer small metadata tables over full rule_labels scans.
    for sql, label in [
        (
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='model_predictions' AND table_name='model_results_prod'
            ORDER BY ordinal_position
            """,
            "model_results_cols",
        ),
        (
            """
            SELECT DISTINCT model_version, rule_index
            FROM model_predictions.model_results_prod
            WHERE task_type = 'color_fill_type' AND rule_index IN (1, 2)
            ORDER BY rule_index, model_version
            LIMIT 50
            """,
            "from_model_results",
        ),
        (
            """
            SELECT model_version, COUNT(*) FROM model_predictions.rule_labels
            WHERE task_type='color_fill_type' AND rule_index=1 AND model_version LIKE 'CF1%%'
            GROUP BY 1 ORDER BY 1 LIMIT 10
            """,
            "cf1_counts",
        ),
    ]:
        try:
            print("trying", label, flush=True)
            cur.execute(sql)
            print(label, cur.fetchall(), flush=True)
        except Exception as e:
            print(label, "ERR", e, flush=True)
print("done", flush=True)
