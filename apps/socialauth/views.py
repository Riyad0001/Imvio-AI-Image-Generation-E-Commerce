
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
import requests
from apps.account.models import User
from rest_framework_simplejwt.views import TokenObtainPairView


class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        id_token = data.get("id_token")
        access_token = data.get("access_token")
        print('data', data)
        print(id_token, access_token)
        if not id_token and not access_token:
            return Response({"error": "Token missing"}, status=400)

        # ---- 1. Validate token with Google ----
        if id_token:
            google_api = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        else:
            google_api = f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}"

        google_response = requests.get(google_api).json()

        # ---- 2. Token invalid ----
        if "email" not in google_response:
            return Response({"error": "Invalid Google token"}, status=400)

        email = google_response["email"]
        name = google_response.get("name", "")
        picture = google_response.get("picture", "")

        # ---- 3. Create user if not exist ----
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": name}
        )

        # ---- 4. Generate JWT tokens ----
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful",
            "is_new_user": created,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "email": user.email,
                "name": user.first_name,
                "photo": picture,
            }
        }, status=200)