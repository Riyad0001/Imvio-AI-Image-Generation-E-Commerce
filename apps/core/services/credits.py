from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import CreditTransaction, CreditWallet


def get_or_create_wallet(user):
    wallet, _ = CreditWallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def add_credits(user, amount, source, reference="", metadata=None):
    if amount <= 0:
        raise ValidationError("Credit amount must be greater than zero")

    wallet = CreditWallet.objects.select_for_update().get_or_create(user=user)[0]
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])

    CreditTransaction.objects.create(
        user=user,
        wallet=wallet,
        entry_type=CreditTransaction.EntryType.CREDIT_IN,
        source=source,
        amount=amount,
        balance_after=wallet.balance,
        reference=reference,
        metadata=metadata or {},
    )
    return wallet


@transaction.atomic
def deduct_credits(user, amount, source, reference="", metadata=None):
    if amount <= 0:
        raise ValidationError("Credit amount must be greater than zero")

    wallet = CreditWallet.objects.select_for_update().get_or_create(user=user)[0]
    if wallet.balance < amount:
        raise ValidationError("Insufficient credits")

    wallet.balance -= amount
    wallet.save(update_fields=["balance", "updated_at"])

    CreditTransaction.objects.create(
        user=user,
        wallet=wallet,
        entry_type=CreditTransaction.EntryType.CREDIT_OUT,
        source=source,
        amount=amount,
        balance_after=wallet.balance,
        reference=reference,
        metadata=metadata or {},
    )
    return wallet
