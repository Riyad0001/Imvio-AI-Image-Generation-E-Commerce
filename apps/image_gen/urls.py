from django.urls import path
from .views import *

urlpatterns = [
    path("images/credit-config/", ImageCreditConfigAPIView.as_view(), name="image-credit-config"),
    path("images/sizes/", ImageSizeListAPIView.as_view(), name="image-size-list"),
    path("images/styles/", ImageStyleListAPIView.as_view(), name="image-style-list"),
    path("images/generate/", GenerateImageAPIView.as_view(), name="generate-image"),
    path("generate-art/", GenerateImageAPIView.as_view(), name="generate-art-legacy"),
    path("images/generation-jobs/<int:job_id>/", GenerationJobDetailAPIView.as_view(), name="generation-job-detail"),
    path("images/history/", ImageHistoryAPIView.as_view(), name="image-history"),
    path("images/<int:image_id>/", ImageDetailAPIView.as_view(), name="image-detail"),
    path("images/<int:image_id>/download/", ImageDownloadAPIView.as_view(), name="image-download"),
    path("images/<int:image_id>/regenerate/", RegenerateImageAPIView.as_view(), name="regenerate-image"),
    path("images/<int:image_id>/save/", SaveImageAPIView.as_view(), name="save-image"),
    path("images/<int:image_id>/share/<uuid:share_id>/", SharedImageAPIView.as_view(), name="shared-image"),
    path("creations/save/", SaveCreationAPIView.as_view(), name="save-creation"),
    path("creations/", CreationListAPIView.as_view(), name="list-creations"),
]