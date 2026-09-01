from django.urls import path
from .views import *


urlpatterns = [

    path("product-types/", ProductTypeListAPIView.as_view()),

    path("product-types/<int:product_type_id>/sizes/", ProductTypeSizeAPIView.as_view()),

    path("calculate-price/", CalculatePriceAPIView.as_view()),

    path("product-types/<int:product_type_id>/pricing/", ProductTypePricingAPIView.as_view()),

    path("other-pages/<str:type>/", Other_pagesView.as_view()),
]