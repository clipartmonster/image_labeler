from django.apps import AppConfig


class LabelImagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'label_images'

    def ready(self):
        import label_images.signals  # noqa: F401
