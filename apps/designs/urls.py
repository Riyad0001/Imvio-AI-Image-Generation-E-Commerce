from django.urls import path
from .views import *

urlpatterns = [
    path("subscribe-mail/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
    path("footer/", FooterDataView.as_view(), name="footer-data"),
    path("contact/", ContactCreateView.as_view(), name="contact-create"),
    path("gen-example/", GenExampleView.as_view(), name="gen-example"),
]
