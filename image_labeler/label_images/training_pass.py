"""Helpers for training pass threshold + attempt limits."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import F, FloatField, Q
from django.db.models.functions import Cast


@dataclass
class TrainingPassStatus:
    passed: bool
    locked: bool
    attempts_used: int
    attempts_granted: int
    attempts_left: int
    best_accuracy: float | None
    pass_threshold: float
    status_label: str  # not_started | in_progress | passed | locked


def _result_accuracy_q(threshold: float) -> Q:
    """Match TrainingResult rows that meet the pass threshold."""
    return Q(total__gt=0) & Q(
        correct__gte=Cast(F("total"), FloatField()) * threshold
    )


def training_results_for_assignment(assignment):
    from .models import TrainingResult

    return TrainingResult.objects.filter(
        user=assignment.user,
        task_type=assignment.task_type,
        rule_index=assignment.rule_index,
    )


def get_training_pass_status(assignment) -> TrainingPassStatus:
    """Compute pass / lock / attempts for one training BatchAssignment."""
    threshold = float(assignment.pass_threshold or 0.975)
    granted = int(assignment.attempts_granted or assignment.max_attempts or 3)
    qs = training_results_for_assignment(assignment).order_by("-completed_at")
    attempts_used = qs.count()

    passed_by_score = qs.filter(_result_accuracy_q(threshold)).exists()
    # Legacy unlock: completed_at was set under the old finish-to-pass rules,
    # before scored attempts existed.
    passed = passed_by_score or (
        assignment.completed_at is not None and attempts_used == 0
    )

    best_accuracy = None
    if attempts_used:
        best_accuracy = max(
            (r.correct / r.total) if r.total else 0.0 for r in qs
        )

    locked = (not passed) and attempts_used >= granted
    attempts_left = max(0, granted - attempts_used) if not passed else 0

    if passed:
        label = "passed"
    elif locked:
        label = "locked"
    elif attempts_used == 0:
        label = "not_started"
    else:
        label = "in_progress"

    return TrainingPassStatus(
        passed=passed,
        locked=locked,
        attempts_used=attempts_used,
        attempts_granted=granted,
        attempts_left=attempts_left,
        best_accuracy=best_accuracy,
        pass_threshold=threshold,
        status_label=label,
    )


def feature_training_passed(user, task_type: str, rule_index: int) -> bool:
    """True when the user has passed training for this feature (or has no training set but completed_at legacy)."""
    from .models import BatchAssignment

    assignment = (
        BatchAssignment.objects.filter(
            user=user,
            task_type=task_type,
            rule_index=rule_index,
            is_training=True,
        )
        .order_by("-id")
        .first()
    )
    if not assignment:
        return False
    return get_training_pass_status(assignment).passed
