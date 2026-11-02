"""Django signals for automatic semantic embedding and match generation."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.items.models import Item

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Item)
def handle_item_post_save(sender, instance, created, **kwargs):
    """Trigger embedding generation and candidate matching when an item is saved."""
    if instance.status in [Item.ItemStatus.RESOLVED, Item.ItemStatus.CLOSED]:
        return

    try:
        from .services import find_and_generate_matches_for_item
        find_and_generate_matches_for_item(instance)
    except Exception as exc:
        logger.warning(
            f"Background automatic matching skipped for item {instance.id}: {exc}"
        )
