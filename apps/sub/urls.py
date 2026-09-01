from django.urls import path
from .views import *
from .api_views import (
    BillingHistoryView,
    BuyCreditsView,
    CreatePrintOrderView,
    OrderDetailView,
    OrderListView,
    SubscribeView,
    SubscriptionInfoView,
    GetCreditPackagesView,
    GetProductSizesView,
    stripe_webhook,
)

urlpatterns = [
    path("subscribe/", CreateCheckoutView.as_view()),
    path("subscription/cancel/", CancelSubscriptionView.as_view()),
    path("subscription/auto-renew/", AutoRenewSubscriptionView.as_view()),
    path("subscription/upgrade/", UpgradeSubscriptionView.as_view()),
    path("subscription/my/", MySubscriptionView.as_view()),
    path("subscription/invoices/", InvoiceHistoryView.as_view()),
    path("webhook/stripe/", stripe_webhook),
    # path("cards/save/", SaveCardView.as_view()),
    path("cards/list/", ListSavedCardsView.as_view()),
    path("payment/success/", StripePaymentSuccessView.as_view()),
    path("payments/buy-credits/", BuyCreditsView.as_view(), name="buy-credits"),
    path("payments/credit-packages/", GetCreditPackagesView.as_view(), name="credit-packages"),
    path("payments/product-sizes/", GetProductSizesView.as_view(), name="product-sizes"),
    path("payments/subscribe/", SubscribeView.as_view(), name="subscribe"),
    path("payments/billing-history/", BillingHistoryView.as_view(), name="billing-history"),
    path("payments/subscription-info/", SubscriptionInfoView.as_view(), name="subscription-info"),
    path("orders/", OrderListView.as_view(), name="orders-list"),
    path("orders/create/", CreatePrintOrderView.as_view(), name="orders-create"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="orders-detail"),
    path("stripe/session-details/",StripeSessionDetailsAPIView.as_view()),    
]