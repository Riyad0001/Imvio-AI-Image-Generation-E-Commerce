from django.urls import path, include

urlpatterns = [
    # path('account/', include('apps.account.urls')),
    # path('auth/', include('apps.socialauth.urls')),
    path('', include('apps.core.urls')),
    path('', include('apps.sub.urls')),
    path('', include('apps.image_gen.urls')),
    path('', include('apps.designs.urls')),
    path('', include('apps.product_mookup.urls')),
]