from django.db import models
from django.contrib.auth.models import User


class listings_to_be_labeled(models.Model):
    unique_id = models.BigIntegerField(primary_key=True)
    date_created = models.DateField()
    theme = models.CharField(max_length=500)
    main_element = models.CharField(max_length=500)
    title = models.CharField(max_length=500)
    description = models.CharField(max_length=500)
    tags = models.CharField(max_length=500)
    primary_colors = models.CharField(max_length=500)
    background_color = models.CharField(max_length=500)
    clip_art_type = models.CharField(max_length=500)
    design_path = models.CharField(max_length=500)
    original_path = models.CharField(max_length=500)

    class Meta:
        db_table = "listings_to_be_labeled"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20,
        choices=[("admin", "Admin"), ("labeler", "Labeler")],
        default="labeler",
    )
    must_change_password = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ---------------------------------------------------------------------------
# BatchAssignment
# ---------------------------------------------------------------------------

WARNING_SEVERITY_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]


class BatchAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="batch_assignments")
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    batch_id = models.IntegerField()
    large_sub_batch = models.IntegerField()
    payment_amount = models.DecimalField(max_digits=8, decimal_places=2)
    bonus_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    deadline = models.DateTimeField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    deadline_warning_severity = models.CharField(
        max_length=10,
        choices=WARNING_SEVERITY_CHOICES,
        default="medium",
    )
    num_labelers_target = models.PositiveIntegerField(default=2)
    gold_percentage = models.FloatField(
        default=5.0,
        help_text="Percent of gold-standard assets to inject when serving this batch.",
    )
    is_training = models.BooleanField(
        default=False,
        help_text="Training batch — shows correct answers after labeler responds.",
    )

    class Meta:
        unique_together = ("user", "task_type", "rule_index", "batch_id", "large_sub_batch")

    def __str__(self):
        return f"{self.user.username} — {self.task_type} batch {self.batch_id}/{self.large_sub_batch}"


class LabelingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="labeling_sessions")
    batch_assignment = models.ForeignKey(BatchAssignment, on_delete=models.CASCADE, related_name="sessions")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    labels_completed = models.IntegerField(default=0)
    active_seconds = models.IntegerField(null=True, blank=True)

    @property
    def duration_hours(self):
        if self.active_seconds is not None:
            return self.active_seconds / 3600
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds() / 3600
        return None

    @property
    def labels_per_hour(self):
        hours = self.duration_hours
        if hours and hours > 0:
            return self.labels_completed / hours
        return None

    def __str__(self):
        return f"{self.user.username} session on {self.started_at:%Y-%m-%d %H:%M}"


class RuleExample(models.Model):
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    label = models.CharField(max_length=10, choices=[("yes", "Yes"), ("no", "No")])
    image_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["task_type", "rule_index", "label"]

    def __str__(self):
        return f"{self.task_type} rule {self.rule_index} — {self.label}"


# ---------------------------------------------------------------------------
# Training results — recorded when a labeler completes a training batch
# ---------------------------------------------------------------------------

class TrainingResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_results")
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    total = models.IntegerField()
    correct = models.IntegerField()
    time_seconds = models.IntegerField(help_text="Wall-clock seconds from start to finish")
    completed_at = models.DateTimeField(auto_now_add=True)

    @property
    def accuracy(self):
        return self.correct / self.total if self.total > 0 else 0

    def __str__(self):
        return f"{self.user.username} {self.task_type}/rule{self.rule_index}: {self.correct}/{self.total}"


class TrainingLabelResponse(models.Model):
    """Per-asset answer recorded when a labeler completes a training session."""
    assignment = models.ForeignKey(
        BatchAssignment, on_delete=models.CASCADE, related_name="training_responses",
    )
    training_result = models.ForeignKey(
        TrainingResult, on_delete=models.CASCADE, related_name="label_responses",
    )
    asset_id = models.BigIntegerField()
    user_answer = models.CharField(max_length=10, help_text="yes, no, or none")
    is_correct = models.BooleanField()

    class Meta:
        indexes = [models.Index(fields=["assignment", "asset_id"])]

    def __str__(self):
        return f"Training {self.asset_id}: {self.user_answer}"


# ---------------------------------------------------------------------------
# Training batch assets — reconciled assets assigned for labeler training
# ---------------------------------------------------------------------------

class TrainingBatchAsset(models.Model):
    assignment = models.ForeignKey(
        BatchAssignment, on_delete=models.CASCADE, related_name="training_assets",
    )
    asset_id = models.BigIntegerField()
    image_link = models.CharField(max_length=500)
    correct_label = models.IntegerField(help_text="Reconciled label: 1=yes, 0=no")

    class Meta:
        unique_together = ("assignment", "asset_id")
        indexes = [models.Index(fields=["assignment"])]

    def __str__(self):
        return f"Training asset {self.asset_id} for {self.assignment}"


# ---------------------------------------------------------------------------
# Rule Guide — editable rule reference content
# ---------------------------------------------------------------------------

class RuleGuide(models.Model):
    """Top-level rule for a given feature (task_type + rule_index).
    Stores the human-readable title, overview description, and display order.
    """
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=100, blank=True,
        help_text="Grouping label shown as a tab, e.g. 'Asset Type', 'Clip Art Type'.",
    )
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("task_type", "rule_index")
        ordering = ["category", "display_order", "rule_index"]

    def __str__(self):
        return f"{self.category} — {self.title} ({self.task_type}, {self.rule_index})"


class RuleDirective(models.Model):
    """A numbered directive within a RuleGuide."""
    guide = models.ForeignKey(RuleGuide, on_delete=models.CASCADE, related_name="directives")
    number = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["number"]
        unique_together = ("guide", "number")

    def __str__(self):
        return f"#{self.number}: {self.text[:60]}"


class RuleReferenceImage(models.Model):
    """An optional reference image attached to a RuleGuide or a specific directive."""
    guide = models.ForeignKey(RuleGuide, on_delete=models.CASCADE, related_name="reference_images")
    directive = models.ForeignKey(
        RuleDirective, on_delete=models.CASCADE, null=True, blank=True,
        related_name="reference_images",
        help_text="If set, image is shown next to this specific directive.",
    )
    image_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True)
    label = models.CharField(
        max_length=10, choices=[("yes", "Yes"), ("no", "No")], blank=True,
        help_text="Whether this image is a YES or NO example.",
    )
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        tag = f" (directive #{self.directive.number})" if self.directive else ""
        return f"Image for {self.guide}{tag}"


# ---------------------------------------------------------------------------
# Gold-standard labels (populated from reconciled assets)
# ---------------------------------------------------------------------------

class GoldStandardLabel(models.Model):
    asset_id = models.BigIntegerField()
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    correct_response = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("asset_id", "task_type", "rule_index")
        indexes = [
            models.Index(fields=["task_type", "rule_index"]),
        ]

    def __str__(self):
        return f"Gold {self.asset_id} {self.task_type}/r{self.rule_index}={self.correct_response}"

