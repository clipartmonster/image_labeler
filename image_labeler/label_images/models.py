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


class BatchAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="batch_assignments")
    task_type = models.CharField(max_length=100)
    rule_index = models.IntegerField()
    batch_id = models.IntegerField()
    large_sub_batch = models.IntegerField()
    payment_amount = models.DecimalField(max_digits=8, decimal_places=2)
    deadline = models.DateTimeField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def duration_hours(self):
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
