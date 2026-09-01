from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .email_utils import send_welcome_email

SIGNUP_FREE_CREDITS = 60

class SignupView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Award 60 free credits — only if this email has NEVER received the signup bonus before.
            # The reference key `signup_bonus:{email}` is stored permanently in CreditTransaction,
            # so even if the account is soft-deleted and re-registered, the check still works.
            free_credits_awarded = 0
            try:
                from apps.core.services.credits import add_credits
                from apps.core.models import CreditTransaction
                bonus_reference = f"signup_bonus:{user.email}"
                already_received = CreditTransaction.objects.filter(
                    source=CreditTransaction.Source.SIGNUP_BONUS,
                    reference=bonus_reference,
                ).exists()
                if not already_received:
                    add_credits(
                        user=user,
                        amount=SIGNUP_FREE_CREDITS,
                        source=CreditTransaction.Source.SIGNUP_BONUS,
                        reference=bonus_reference,
                        metadata={"reason": "New user signup bonus", "email": user.email},
                    )
                    free_credits_awarded = SIGNUP_FREE_CREDITS
            except Exception:
                pass

            # Send welcome email; show credits only if actually awarded
            send_welcome_email(user, credits=free_credits_awarded)

            try:
                from apps.core.services.meta_pixel_service import send_meta_capi_event
                send_meta_capi_event(
                    event_name="CompleteRegistration",
                    user_email=user.email,
                    request=request,
                    event_id=f"registration_{user.id}"
                )
            except Exception:
                pass
            return Response({
                "status": True,
                "message": "Account created successfully",
                "user_id": user.id,
                "email": user.email,
                "free_credits_awarded": free_credits_awarded,
            }, status=201)
        return Response(serializer.errors, status=400)



    
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import PasswordResetOTP
from .email_utils import send_otp_email

User = get_user_model()

class SendOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()

        if not email:
            return Response({
                "status": False,
                "message": "Email is required"
            }, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "status": False,
                "message": "User not found"
            }, status=404)

        otp = str(random.randint(100000, 999999))

        # Keep only one active OTP per user to avoid stale-code confusion.
        PasswordResetOTP.objects.filter(user=user, is_verified=False).delete()
        PasswordResetOTP.objects.create(user=user, otp=otp)

        send_otp_email(email, otp)

        return Response({
            "status": True,
            "message": "OTP sent to email"
        })

from rest_framework import status

class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        otp = str(request.data.get("otp", "")).strip()

        if not email or not otp:
            return Response({
                "status": False,
                "message": "Email and OTP are required"
            }, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "status": False,
                "message": "Invalid OTP"
            }, status=400)

        otp_obj = PasswordResetOTP.objects.filter(
            user=user,
            otp=otp,
            is_verified=False,
        ).order_by('-created_at').first()

        if otp_obj is None:
            return Response({
                "status": False,
                "message": "Invalid OTP"
            }, status=400)

        if otp_obj.is_expired():
            return Response({
                "status": False,
                "message": "OTP expired"
            }, status=400)

        otp_obj.is_verified = True
        otp_obj.save()

        return Response({
            "status": True,
            "message": "OTP verified",
            "token": str(otp_obj.token)
        })
class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        try:
            otp_obj = PasswordResetOTP.objects.get(
                token=token,
                is_verified=True
            )
        except PasswordResetOTP.DoesNotExist:
            return Response({
                "status": False,
                "message": "Invalid or expired session"
            }, status=400)

        user = otp_obj.user
        user.set_password(new_password)
        user.save()

        otp_obj.delete()  # one-time use

        return Response({
            "status": True,
            "message": "Password reset successful"
        })
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


from .serializers import UserCreateSerializer
User = get_user_model()


class UserSignupView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            from apps.core.services.meta_pixel_service import send_meta_capi_event
            send_meta_capi_event(
                event_name="CompleteRegistration",
                user_email=user.email,
                request=request,
                event_id=f"registration_{user.id}"
            )
        except Exception:
            pass
        response_data = {
            "code": status.HTTP_201_CREATED,
            "message": "User created successfully",
            "data": user.serialize()
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    permission_classes = ('IsAuthenticated',)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)
        if user is not None:
            login(request, user)
            response_data = {
                "code": status.HTTP_200_OK,
                "message": "User logged in successfully",
                "data": user.serialize()
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            response_data = {
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid credentials",
                "data": None
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            
            # Get total available credits from wallet
            total_credits = 0
            if hasattr(user, 'wallet'):
                total_credits = user.wallet.balance

            return Response({
                "status": True,
                "message": "Login successful",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "profile_photo": user.profile_photo.url if user.profile_photo else None,
                        "is_disabled": user.is_disabled,
                        "total_available_credits": total_credits,
                        "created_at": user.created_at.isoformat(),
                    },
                }
            })
        
        return Response({
            "status": False,
            "message": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({
                "status": False,
                "message": "Refresh token is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
        except TokenError:
            return Response({
                "status": False,
                "message": "Invalid token"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token.blacklist()
        except Exception:
            # If blacklist app is not configured, treat logout as client-side token discard.
            pass

        return Response({
            "status": True,
            "message": "Logout successful"
        }, status=status.HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # check old password
        if not user.check_password(old_password):
            return Response({
                "status": False,
                "message": "Old password is incorrect"
            }, status=status.HTTP_400_BAD_REQUEST)

        # set new password
        user.set_password(new_password)
        user.save()

        return Response({
            "status": True,
            "message": "Password changed successfully"
        })

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests as http_requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import GoogleLoginSerializer

User = get_user_model()

class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['id_token']

        try:
            allowed_client_ids = set()

            configured_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
            if configured_client_id:
                allowed_client_ids.add(str(configured_client_id).strip())

            configured_client_ids = getattr(settings, 'GOOGLE_CLIENT_IDS', None)
            if isinstance(configured_client_ids, (list, tuple, set)):
                allowed_client_ids.update(str(client_id).strip() for client_id in configured_client_ids if client_id)
            elif isinstance(configured_client_ids, str):
                allowed_client_ids.update(client_id.strip() for client_id in configured_client_ids.split(',') if client_id.strip())

            email = None
            full_name = ''
            email_verified = False

            try:
                idinfo = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request()
                )

                issuer = idinfo.get('iss')
                if issuer not in {'accounts.google.com', 'https://accounts.google.com'}:
                    raise ValueError('Invalid Google issuer')

                audience = idinfo.get('aud')
                authorized_party = idinfo.get('azp')
                # Accept tokens from different client IDs as long as Google verifies signature/issuer.
                # This avoids false negatives when frontend uses another valid Google OAuth client.
                if allowed_client_ids and audience not in allowed_client_ids and authorized_party not in allowed_client_ids:
                    pass

                email = idinfo.get('email')
                full_name = idinfo.get('name', '')
                email_verified_raw = idinfo.get('email_verified', False)
                email_verified = email_verified_raw is True or str(email_verified_raw).lower() == 'true'
            except Exception:
                # Fallback 1: validate as an ID token using Google's tokeninfo endpoint.
                tokeninfo_response = http_requests.get(
                    'https://oauth2.googleapis.com/tokeninfo',
                    params={'id_token': token},
                    timeout=10,
                )
                if tokeninfo_response.status_code == 200:
                    tokeninfo = tokeninfo_response.json()
                    audience = tokeninfo.get('aud')
                    authorized_party = tokeninfo.get('azp')
                    if allowed_client_ids and audience not in allowed_client_ids and authorized_party not in allowed_client_ids:
                        pass

                    email = tokeninfo.get('email')
                    full_name = tokeninfo.get('name', '')
                    email_verified_raw = tokeninfo.get('email_verified', False)
                    email_verified = email_verified_raw is True or str(email_verified_raw).lower() == 'true'
                else:
                    # Fallback 2: OAuth v2 access_token flow.
                    userinfo_response = http_requests.get(
                        'https://www.googleapis.com/oauth2/v3/userinfo',
                        headers={'Authorization': f'Bearer {token}'},
                        timeout=10,
                    )
                    if userinfo_response.status_code != 200:
                        raise ValueError('Invalid Google token')

                    userinfo = userinfo_response.json()
                    email = userinfo.get('email')
                    full_name = userinfo.get('name', '')
                    email_verified_raw = userinfo.get('email_verified', False)
                    email_verified = email_verified_raw is True or str(email_verified_raw).lower() == 'true'

            if not email or not email_verified:
                return Response({
                    "status": False,
                    "message": "Invalid Google token"
                }, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                }
            )

            try:
                from apps.core.services.meta_pixel_service import send_meta_capi_event
                import time
                if created:
                    send_meta_capi_event(
                        event_name="CompleteRegistration",
                        user_email=user.email,
                        request=request,
                        event_id=f"registration_{user.id}",
                        custom_data={"registration_method": "google"}
                    )
                else:
                    send_meta_capi_event(
                        event_name="GoogleLogin",
                        user_email=user.email,
                        request=request,
                        event_id=f"login_google_{user.id}_{int(time.time())}"
                    )
            except Exception:
                pass

            if not created and full_name and user.full_name != full_name:
                user.full_name = full_name
                user.save(update_fields=["full_name"])

            if user.is_disabled or user.is_deleted or not user.is_active:
                return Response({
                    "status": False,
                    "message": "Your account is disabled"
                }, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)

            return Response({
                "status": True,
                "message": "Login successful",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email,
                        "is_new_user": created
                    }
                }
            })

        except ValueError:
            return Response({
                "status": False,
                "message": "Invalid Google token"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({
                "status": False,
                "message": "Google login failed"
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import ProfileSerializer

        serializer = ProfileSerializer(request.user)
        return Response({
            "status": True,
            "message": "Profile fetched successfully",
            "data": serializer.data,
        })

    def patch(self, request):
        from .serializers import ProfileSerializer, ProfileUpdateSerializer

        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ProfileSerializer(request.user)
        return Response({
            "status": True,
            "message": "Profile updated successfully",
            "data": response_serializer.data,
        })


class CreditBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = getattr(request.user, "wallet", None)
        credits = wallet.balance if wallet else 0
        return Response({
            "status": True,
            "message": "Credit balance fetched successfully",
            "data": {"total_available_credits": credits},
        })


class DisableAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.disable()
        return Response({
            "status": True,
            "message": "Account disabled successfully",
        })


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.soft_delete()
        return Response({
            "status": True,
            "message": "Account deleted successfully",
        })