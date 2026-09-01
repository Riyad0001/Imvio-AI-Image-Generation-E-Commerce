from .models import Subscription, PlanFeature

def has_feature(user, feature_key):
    subscription = (
        Subscription.objects
        .filter(user=user, is_active=True)
        .select_related("plan")
        .first()
    )

    if not subscription:
        return False

    return PlanFeature.objects.filter(
        plan=subscription.plan,
        feature__key=feature_key,
        is_enabled=True
    ).exists()


def get_feature_limit(user, feature_key):
    subscription = Subscription.objects.filter(
        user=user, is_active=True
    ).first()

    if not subscription:
        return None

    pf = PlanFeature.objects.filter(
        plan=subscription.plan,
        feature__key=feature_key,
        is_enabled=True
    ).first()

    return pf.limit_value if pf else None