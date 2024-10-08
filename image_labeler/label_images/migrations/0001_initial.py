# Generated by Django 5.0.7 on 2024-07-22 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='listings_to_be_labeled',
            fields=[
                ('unique_id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('date_created', models.DateField()),
                ('theme', models.CharField(max_length=500)),
                ('main_element', models.CharField(max_length=500)),
                ('title', models.CharField(max_length=500)),
                ('description', models.CharField(max_length=500)),
                ('tags', models.CharField(max_length=500)),
                ('primary_colors', models.CharField(max_length=500)),
                ('background_color', models.CharField(max_length=500)),
                ('clip_art_type', models.CharField(max_length=500)),
                ('design_path', models.CharField(max_length=500)),
                ('original_path', models.CharField(max_length=500)),
            ],
            options={
                'db_table': 'listings_to_be_labeled',
            },
        ),
    ]
