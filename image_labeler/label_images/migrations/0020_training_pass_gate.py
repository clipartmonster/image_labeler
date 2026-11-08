from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("label_images", "0019_selected_image_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchassignment",
            name="pass_threshold",
            field=models.FloatField(
                default=0.975,
                help_text="Minimum accuracy (0–1) required to pass this training assignment.",
            ),
        ),
        migrations.AddField(
            model_name="batchassignment",
            name="max_attempts",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Initial number of practice attempts granted for this training set.",
            ),
        ),
        migrations.AddField(
            model_name="batchassignment",
            name="attempts_granted",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Total attempts allowed (raised by admin when granting more practice).",
            ),
        ),
        migrations.AddField(
            model_name="batchassignment",
            name="source_batch_id",
            field=models.IntegerField(
                blank=True,
                help_text="Labeling batch_id assets were sampled from (training only).",
                null=True,
            ),
        ),
    ]
