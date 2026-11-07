from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("label_images", "0018_trainingexemption"),
    ]

    operations = [
        migrations.CreateModel(
            name="SelectedImageBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_number", models.PositiveIntegerField(unique=True)),
                ("title", models.CharField(blank=True, max_length=200)),
                ("filters", models.JSONField(default=list)),
                ("sample_size", models.PositiveIntegerField(default=100)),
                ("pool_size", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["batch_number"],
            },
        ),
        migrations.CreateModel(
            name="SelectedImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.BigIntegerField()),
                ("image_link", models.TextField()),
                ("position", models.PositiveIntegerField(default=0)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="label_images.selectedimagebatch",
                    ),
                ),
            ],
            options={
                "ordering": ["position"],
                "unique_together": {("batch", "position")},
            },
        ),
        migrations.AddIndex(
            model_name="selectedimage",
            index=models.Index(fields=["batch", "position"], name="label_image_batch_i_7c4a1e_idx"),
        ),
    ]
