from django.db import models

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
        db_table = 'listings_to_be_labeled'
