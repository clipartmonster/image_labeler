import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('label_images', '0012_add_bonus_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingLabelResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_id', models.BigIntegerField()),
                ('user_answer', models.CharField(help_text='yes, no, or none', max_length=10)),
                ('is_correct', models.BooleanField()),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_responses', to='label_images.batchassignment')),
                ('training_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='label_responses', to='label_images.trainingresult')),
            ],
            options={
                'indexes': [models.Index(fields=['assignment', 'asset_id'], name='label_image_assignm_8a3f2d_idx')],
            },
        ),
    ]
