from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_root_folder(sender, instance, created, **kwargs):
    """Create a root folder for every new user."""
    if not created:
        return
    try:
        from apps.files.models import Folder
        Folder.objects.get_or_create(
            owner=instance,
            name='My Files',
            parent=None,
        )
    except Exception:
        # files app may not be migrated yet during tests / initial setup
        pass
