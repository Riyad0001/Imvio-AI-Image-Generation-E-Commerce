from django.urls import path
from . import views

urlpatterns = [
    path('google/', views.GoogleLoginAPIView.as_view()),
]