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
        db_table = 'listings_to_be_labeled'


ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('labeler', 'Labeler'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='labeler')

    class Meta:
        db_table = 'auth_user_profile'

    def __str__(self):
        return f"{self.user.username} ({self.role})"
