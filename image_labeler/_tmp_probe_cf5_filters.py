from django.conf import settings
from django.db import connections

db = "prod" if "prod" in settings.DATABASES else "default"
with connections[db].cursor() as cur:
    cur.execute(
        """
        SELECT table_schema, table_name FROM information_schema.tables
        WHERE table_schema = 'model_predictions'
          AND (
            table_name ILIKE '%multi%'
            OR table_name ILIKE '%paint%'
            OR table_name ILIKE '%depth%'
            OR table_name = 'rule_labels'
            OR table_name ILIKE '%mono%'
          )
        ORDER BY 1, 2
        """
    )
    print("tables", cur.fetchall())
    cur.execute(
        """
        SELECT model_version, rule_index, label, COUNT(*)
        FROM model_predictions.rule_labels
        WHERE task_type = 'color_fill_type' AND rule_index IN (1, 2, 5)
        GROUP BY 1, 2, 3
        ORDER BY 2, 1, 3
        """
    )
    print("cf_labels")
    for r in cur.fetchall():
        print(r)

    # quick pool count for proposed filters
    cur.execute(
        """
        SELECT COUNT(*)
        FROM model_predictions.stage_multi_color m
        JOIN model_predictions.rule_labels d
          ON d.asset_id = m.asset_id
         AND d.task_type = 'color_fill_type'
         AND d.rule_index = 2
         AND d.label = 1
        JOIN model_predictions.rule_labels p
          ON p.asset_id = m.asset_id
         AND p.task_type = 'color_fill_type'
         AND p.rule_index = 1
         AND p.label = 0
        JOIN content.assets a ON a.asset_id = m.asset_id
        WHERE a.s3 = TRUE
          AND a.image_link IS NOT NULL
          AND a.image_link <> ''
        """
    )
    print("pool_no_version_filter", cur.fetchone()[0])

    # with latest versions if present
    cur.execute(
        """
        SELECT DISTINCT model_version
        FROM model_predictions.rule_labels
        WHERE task_type = 'color_fill_type' AND rule_index = 1
        ORDER BY 1
        """
    )
    print("paint_versions", [r[0] for r in cur.fetchall()])
    cur.execute(
        """
        SELECT DISTINCT model_version
        FROM model_predictions.rule_labels
        WHERE task_type = 'color_fill_type' AND rule_index = 2
        ORDER BY 1
        """
    )
    print("depth_versions", [r[0] for r in cur.fetchall()])
