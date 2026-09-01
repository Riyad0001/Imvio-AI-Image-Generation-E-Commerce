from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import CreditWallet, User


@receiver(post_save, sender=User)
def create_wallet_for_user(sender, instance, created, **kwargs):
    if created:
        CreditWallet.objects.get_or_create(user=instance)
