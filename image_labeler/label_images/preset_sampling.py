"""Fast preset sampling for review / labeling batch creation.

Avoids ``ORDER BY random()`` over multi-table ``rule_labels`` joins (very slow).
Instead: take an asset_id-ordered window from the stage table, then apply rule /
density filters only on that small candidate set. Repeat until filled.
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
import urllib3
from django.conf import settings
from django.db import connections

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "image/jpeg,image/png,image/webp,image/apng,image/*;q=0.8,*/*;q=0.5",
}

STAGE_TABLE = {
    "mono": "model_predictions.stage_mono_color",
    "multi": "model_predictions.stage_multi_color",
}

# Named presets for review grids and labeling queues.
PRESETS = {
    "sketch_fill_v2_low_density": {
        "title": "Sketch Fill V2 candidates · mono-color · low density",
        "filters": [
            "Mono-color clip art (stage_mono_color)",
            "Sketch Fill V2 candidate: Sketch Elements CF7_0.01 = True",
            "Color pixel density ratio < 0.3 (CD1_0.01)",
            "S3 image available",
        ],
        "color_stage": "mono",
        "require_cf7": True,
        "min_density": None,
        "max_density": 0.3,
        "min_complexity": None,
        "max_complexity": None,
        "rule_filters": [],
    },
    "cf5_solid_high_density": {
        "title": "Color Depth (rule 5) solid · mono · density 0.97–0.99",
        "filters": [
            "Mono-color clip art (stage_mono_color)",
            "Color pixel density ratio 0.97–0.99 (CD1_0.01)",
            "S3 image available",
        ],
        "color_stage": "mono",
        "require_cf7": False,
        "min_density": 0.97,
        "max_density": 0.99,
        "min_complexity": None,
        "max_complexity": None,
        "rule_filters": [],
    },
    "cf5_multi_depth_yes_paint_no": {
        "title": (
            "Color Depth Scale (rule 5) · multi-color · "
            "color depth=yes · paint fill=no · gradient=no"
        ),
        "filters": [
            "Multi-color clip art (stage_multi_color)",
            "Color Depth (CF rule 2) = yes (CF2_0.03)",
            "Paint Fill (CF rule 1) = no (CF1_0.01)",
            "Gradient (CF rule 8) = no (CF8_0.01)",
            "S3 image available",
        ],
        "color_stage": "multi",
        "require_cf7": False,
        "min_density": None,
        "max_density": None,
        "min_complexity": None,
        "max_complexity": None,
        "rule_filters": [
            {
                "alias": "rd",
                "task_type": "color_fill_type",
                "rule_index": 2,
                "model_version": "CF2_0.03",
                "label": 1,
            },
            {
                "alias": "rp",
                "task_type": "color_fill_type",
                "rule_index": 1,
                "model_version": "CF1_0.01",
                "label": 0,
            },
            {
                "alias": "rg",
                "task_type": "color_fill_type",
                "rule_index": 8,
                "model_version": "CF8_0.01",
                "label": 0,
            },
        ],
    },
}


def _filter_sql_parts(preset: dict[str, Any]) -> tuple[list[str], list[str], list]:
    """Return (extra_joins, where_clauses, params) applied on alias ``c`` candidates."""
    joins: list[str] = []
    where: list[str] = []
    params: list = []

    needs_density = (
        preset.get("min_density") is not None or preset.get("max_density") is not None
    )
    if needs_density:
        joins.append(
            "JOIN model_predictions.color_pixel_density d ON d.asset_id = c.asset_id"
        )
        where.extend(
            [
                "d.model_version = 'CD1_0.01'",
                "d.ratio = d.ratio",
                "d.ratio <> 'Infinity'::float8",
                "d.ratio <> '-Infinity'::float8",
            ]
        )
        if preset["min_density"] is not None:
            where.append("d.ratio > %s")
            params.append(float(preset["min_density"]))
        if preset["max_density"] is not None:
            where.append("d.ratio < %s")
            params.append(float(preset["max_density"]))

    if (
        preset.get("min_complexity") is not None
        or preset.get("max_complexity") is not None
    ):
        joins.append(
            "JOIN model_predictions.color_complexity cx "
            "ON cx.asset_id = c.asset_id::text"
        )
        where.append("cx.model_version = 'CO1_0.01'")
        if preset.get("min_complexity") is not None:
            where.append("cx.entropy >= %s")
            params.append(float(preset["min_complexity"]))
        if preset.get("max_complexity") is not None:
            where.append("cx.entropy <= %s")
            params.append(float(preset["max_complexity"]))

    if preset.get("require_cf7"):
        joins.append(
            "JOIN model_predictions.rule_labels r ON r.asset_id = c.asset_id"
        )
        where.extend(
            [
                "r.task_type = 'color_fill_type'",
                "r.rule_index = 7",
                "r.model_version = 'CF7_0.01'",
                "r.label = 1",
            ]
        )

    for rf in preset.get("rule_filters") or []:
        alias = rf["alias"]
        joins.append(
            f"JOIN model_predictions.rule_labels {alias} "
            f"ON {alias}.asset_id = c.asset_id"
        )
        where.extend(
            [
                f"{alias}.task_type = %s",
                f"{alias}.rule_index = %s",
                f"{alias}.model_version = %s",
                f"{alias}.label = %s",
            ]
        )
        params.extend(
            [
                rf["task_type"],
                int(rf["rule_index"]),
                rf["model_version"],
                int(rf["label"]),
            ]
        )

    return joins, where, params


def image_url_loads(url: str, timeout: float = 8.0) -> bool:
    """True when ``url`` returns image bytes the color-depth sampler can use."""
    if not isinstance(url, str) or not url.startswith("http"):
        return False
    try:
        with requests.get(
            url,
            headers=_IMAGE_HEADERS,
            timeout=timeout,
            stream=True,
            verify=False,
            allow_redirects=True,
        ) as resp:
            if resp.status_code != 200:
                return False
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype.startswith("image/"):
                # Read a small prefix so we fail fast on empty/HTML bodies.
                next(resp.iter_content(chunk_size=2048), None)
                return True
            return False
    except Exception:
        return False


def filter_loadable_images(
    candidates: list[dict], *, workers: int = 16
) -> list[dict]:
    """Keep only candidates whose ``image_link`` successfully loads as an image."""
    if not candidates:
        return []
    kept: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(image_url_loads, item["image_link"]): item for item in candidates
        }
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                kept.append(item)
    return kept


def sample_preset_assets(
    preset: dict[str, Any],
    sample_size: int,
    *,
    exclude_ids: set[int] | None = None,
    seed: int | None = None,
    window: int | None = None,
    max_attempts: int = 40,
    verify_images: bool = False,
    verify_workers: int = 16,
) -> list[dict]:
    """Return up to ``sample_size`` ``{asset_id, image_link}`` dicts for ``preset``.

    When ``verify_images`` is True, oversample and drop URLs that do not load as
    images (so the color-depth canvas/proxy path will work).
    """
    stage = preset.get("color_stage", "mono")
    if stage not in STAGE_TABLE:
        raise ValueError(f"Unknown color_stage={stage!r}")

    exclude_ids = set(exclude_ids or [])
    rng = random.Random(seed)
    # Oversample when verifying so broken links don't leave us short.
    fetch_size = sample_size * 3 if verify_images else sample_size
    window = window or max(fetch_size * 40, 4000)
    db = "prod" if "prod" in settings.DATABASES else "default"
    stage_table = STAGE_TABLE[stage]
    filter_joins, filter_where, filter_params = _filter_sql_parts(preset)

    selected: list[dict] = []
    seen: set[int] = set(exclude_ids)

    with connections[db].cursor() as cur:
        cur.execute(f"SELECT MIN(asset_id), MAX(asset_id) FROM {stage_table}")
        min_id, max_id = cur.fetchone()
        if min_id is None or max_id is None:
            return []

        for _ in range(max_attempts):
            if len(selected) >= fetch_size:
                break
            start_id = rng.randint(int(min_id), int(max_id))
            need = fetch_size - len(selected)
            cand_limit = max(window, need * 20)

            cand_where = [
                "a.s3 = TRUE",
                "a.image_link IS NOT NULL",
                "a.image_link <> ''",
                "m.asset_id >= %s",
            ]
            cand_params: list = [start_id]
            if seen:
                cand_where.append("NOT (m.asset_id = ANY(%s))")
                cand_params.append(list(seen))

            sql = (
                "WITH candidates AS (\n"
                "  SELECT m.asset_id, a.image_link\n"
                f"  FROM {stage_table} m\n"
                "  JOIN content.assets a ON a.asset_id = m.asset_id\n"
                "  WHERE "
                + "\n    AND ".join(cand_where)
                + "\n  ORDER BY m.asset_id\n"
                "  LIMIT %s\n"
                ")\n"
                "SELECT c.asset_id, c.image_link\n"
                "FROM candidates c\n"
                + ("\n".join(filter_joins) + "\n" if filter_joins else "")
                + (
                    ("WHERE " + "\n  AND ".join(filter_where) + "\n")
                    if filter_where
                    else ""
                )
                + "LIMIT %s"
            )
            params = cand_params + [cand_limit] + filter_params + [need * 5]
            cur.execute(sql, params)
            rows = cur.fetchall()
            if not rows and start_id > min_id:
                # wrap: try from the beginning of the id range
                continue
            for asset_id, image_link in rows:
                if asset_id in seen:
                    continue
                seen.add(asset_id)
                selected.append({"asset_id": asset_id, "image_link": image_link})
                if len(selected) >= fetch_size:
                    break

            # If we started high and got few rows, also sweep from min once.
            if len(rows) < cand_limit // 4 and start_id > min_id:
                cand_params2: list = [int(min_id)]
                cand_where2 = [
                    "a.s3 = TRUE",
                    "a.image_link IS NOT NULL",
                    "a.image_link <> ''",
                    "m.asset_id >= %s",
                ]
                if seen:
                    cand_where2.append("NOT (m.asset_id = ANY(%s))")
                    cand_params2.append(list(seen))
                sql2 = (
                    "WITH candidates AS (\n"
                    "  SELECT m.asset_id, a.image_link\n"
                    f"  FROM {stage_table} m\n"
                    "  JOIN content.assets a ON a.asset_id = m.asset_id\n"
                    "  WHERE "
                    + "\n    AND ".join(cand_where2)
                    + "\n  ORDER BY m.asset_id\n"
                    "  LIMIT %s\n"
                    ")\n"
                    "SELECT c.asset_id, c.image_link\n"
                    "FROM candidates c\n"
                    + ("\n".join(filter_joins) + "\n" if filter_joins else "")
                    + (
                        ("WHERE " + "\n  AND ".join(filter_where) + "\n")
                        if filter_where
                        else ""
                    )
                    + "LIMIT %s"
                )
                cur.execute(
                    sql2, cand_params2 + [cand_limit] + filter_params + [need * 5]
                )
                for asset_id, image_link in cur.fetchall():
                    if asset_id in seen:
                        continue
                    seen.add(asset_id)
                    selected.append({"asset_id": asset_id, "image_link": image_link})
                    if len(selected) >= fetch_size:
                        break

    if verify_images:
        selected = filter_loadable_images(selected, workers=verify_workers)

    return selected[:sample_size]
