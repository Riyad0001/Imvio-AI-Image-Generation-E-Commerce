from django.urls import path
from .views import *

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('user-signup/', UserSignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('session-login/', UserLoginView.as_view(), name='session-login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('password/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('password/change/', ChangePasswordView.as_view(), name='change-password'),
    path('social/google/', GoogleLoginView.as_view(), name='google-login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/credits/', CreditBalanceView.as_view(), name='credit-balance'),
    path('account/disable/', DisableAccountView.as_view(), name='disable-account'),
    path('account/', DeleteAccountView.as_view(), name='delete-account'),
]
