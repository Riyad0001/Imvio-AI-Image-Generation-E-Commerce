import json
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from unfold.components import BaseComponent, register_component


def _last_30_labels():
    today = timezone.now().date()
    return [(today - timedelta(days=29 - i)) for i in range(30)]


def _fill_daily(qs_dict, dates):
    return [qs_dict.get(d, 0) for d in dates]


# ─── User Registration Chart ──────────────────────────────────────────────────

@register_component
class UserRegistrationChartComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        from apps.core.models import User

        context = super().get_context_data(**kwargs)
        dates = _last_30_labels()

        qs = (
            User.all_objects.filter(
                created_at__date__gte=dates[0],
                created_at__date__lte=dates[-1],
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )
        day_map = {row["day"]: row["count"] for row in qs}
        values = _fill_daily(day_map, dates)

        context.update({
            "height": 260,
            "data": json.dumps({
                "labels": [d.strftime("%b %d") for d in dates],
                "datasets": [
                    {
                        "label": "New Users",
                        "data": values,
                        "borderColor": "rgba(99,102,241,1)",
                        "backgroundColor": "rgba(99,102,241,0.15)",
                        "fill": True,
                        "tension": 0.4,
                    }
                ],
            }),
        })
        return context


# ─── Revenue Chart ────────────────────────────────────────────────────────────

@register_component
class RevenueChartComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        from apps.sub.models import BillingHistory

        context = super().get_context_data(**kwargs)
        dates = _last_30_labels()

        def get_revenue_series(billing_type, color):
            qs = (
                BillingHistory.objects.filter(
                    status=BillingHistory.Status.PAID,
                    billing_type=billing_type,
                    created_at__date__gte=dates[0],
                    created_at__date__lte=dates[-1],
                )
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(total=Sum("amount"))
            )
            day_map = {row["day"]: float(row["total"]) for row in qs}
            return {
                "label": billing_type.replace("_", " ").title(),
                "data": _fill_daily(day_map, dates),
                "backgroundColor": color,
                "borderRadius": 4,
            }

        context.update({
            "height": 260,
            "data": json.dumps({
                "labels": [d.strftime("%b %d") for d in dates],
                "datasets": [
                    get_revenue_series(BillingHistory.BillingType.SUBSCRIPTION, "rgba(16,185,129,0.8)"),
                    get_revenue_series(BillingHistory.BillingType.CREDIT_PURCHASE, "rgba(99,102,241,0.8)"),
                    get_revenue_series(BillingHistory.BillingType.PRINT_ORDER, "rgba(245,158,11,0.8)"),
                ],
            }),
        })
        return context


# ─── Image Generation Chart ───────────────────────────────────────────────────

@register_component
class ImageGenerationChartComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        from apps.image_gen.models import ImageGenerationJob

        context = super().get_context_data(**kwargs)
        dates = _last_30_labels()

        qs = (
            ImageGenerationJob.objects.filter(
                created_at__date__gte=dates[0],
                created_at__date__lte=dates[-1],
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )
        day_map = {row["day"]: row["count"] for row in qs}
        values = _fill_daily(day_map, dates)

        context.update({
            "height": 260,
            "data": json.dumps({
                "labels": [d.strftime("%b %d") for d in dates],
                "datasets": [
                    {
                        "label": "Image Jobs",
                        "data": values,
                        "borderColor": "rgba(245,158,11,1)",
                        "backgroundColor": "rgba(245,158,11,0.15)",
                        "fill": True,
                        "tension": 0.4,
                    }
                ],
            }),
        })
        return context


# ─── Order Status Chart ───────────────────────────────────────────────────────

@register_component
class OrderStatusChartComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        from apps.sub.models import PrintOrder

        context = super().get_context_data(**kwargs)

        statuses = [
            PrintOrder.Status.PENDING,
            PrintOrder.Status.PAID,
            PrintOrder.Status.SENT_TO_GELATO,
            PrintOrder.Status.FAILED,
        ]
        labels = ["Pending", "Paid", "Sent to Gelato", "Failed"]
        colors = [
            "rgba(245,158,11,0.8)",
            "rgba(16,185,129,0.8)",
            "rgba(99,102,241,0.8)",
            "rgba(239,68,68,0.8)",
        ]

        counts = []
        for s in statuses:
            counts.append(PrintOrder.objects.filter(status=s).count())

        context.update({
            "height": 260,
            "data": json.dumps({
                "labels": labels,
                "datasets": [
                    {
                        "label": "Orders",
                        "data": counts,
                        "backgroundColor": colors,
                        "borderRadius": 6,
                    }
                ],
            }),
        })
        return context


# ─── Billing Type Distribution Chart ─────────────────────────────────────────

@register_component
class BillingTypeChartComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        from apps.sub.models import BillingHistory

        context = super().get_context_data(**kwargs)

        billing_types = [
            BillingHistory.BillingType.SUBSCRIPTION,
            BillingHistory.BillingType.CREDIT_PURCHASE,
            BillingHistory.BillingType.PRINT_ORDER,
        ]
        labels = ["Subscription", "Credit Purchase", "Print Order"]
        colors = [
            "rgba(16,185,129,0.85)",
            "rgba(99,102,241,0.85)",
            "rgba(245,158,11,0.85)",
        ]

        counts = []
        for bt in billing_types:
            counts.append(
                BillingHistory.objects.filter(
                    status=BillingHistory.Status.PAID,
                    billing_type=bt,
                ).count()
            )

        context.update({
            "height": 260,
            "data": json.dumps({
                "labels": labels,
                "datasets": [
                    {
                        "label": "Transactions",
                        "data": counts,
                        "backgroundColor": colors,
                        "borderRadius": 6,
                    }
                ],
            }),
        })
        return context
