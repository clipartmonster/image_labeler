from django.contrib import admin
from .models import (
    UserProfile, BatchAssignment, LabelingSession, RuleExample,
    RuleGuide, RuleDirective, RuleReferenceImage,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "must_change_password")
    list_filter = ("role", "must_change_password")


@admin.register(BatchAssignment)
class BatchAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "user", "task_type", "rule_index", "batch_id",
        "large_sub_batch", "payment_amount", "bonus_amount", "deadline", "completed_at",
    )
    list_filter = ("user", "task_type", "completed_at")
    search_fields = ("user__username",)


@admin.register(LabelingSession)
class LabelingSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "batch_assignment", "started_at", "ended_at", "labels_completed")
    list_filter = ("user",)
    readonly_fields = ("duration_hours", "labels_per_hour")

    def duration_hours(self, obj):
        val = obj.duration_hours
        return f"{val:.2f} hrs" if val else "—"

    def labels_per_hour(self, obj):
        val = obj.labels_per_hour
        return f"{val:.1f}/hr" if val else "—"


@admin.register(RuleExample)
class RuleExampleAdmin(admin.ModelAdmin):
    list_display = ("task_type", "rule_index", "label", "caption")
    list_filter = ("task_type", "rule_index", "label")


class RuleDirectiveInline(admin.TabularInline):
    model = RuleDirective
    extra = 1


class RuleReferenceImageInline(admin.TabularInline):
    model = RuleReferenceImage
    extra = 0


@admin.register(RuleGuide)
class RuleGuideAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "task_type", "rule_index")
    list_filter = ("category", "task_type")
    inlines = [RuleDirectiveInline, RuleReferenceImageInline]
