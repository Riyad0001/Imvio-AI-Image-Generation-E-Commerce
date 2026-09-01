from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from rest_framework.permissions import IsAuthenticated,AllowAny

class NewsletterSubscribeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Skip token validation
    def post(self, request):
        serializer = NewsletterSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            email = serializer.validated_data["email"]
            subscription = NewsletterSubscription.objects.create(email=email)
            
            return Response(
                {
                    "status": True,
                    "message": "Successfully subscribed to newsletter",
                    "data": {"email": subscription.email},
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class FooterDataView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Skip token validation
    def get(self, request):
        try:
            footer = FooterData.objects.filter().first()
            
            if not footer:
                return Response(
                    {
                        "status": False,
                        "message": "Footer data not found",
                        "data": None,
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = FooterDataSerializer(footer)
            return Response(
                {
                    "status": True,
                    "message": "Footer data retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContactCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Skip token validation

    def post(self, request):
        serializer = ContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            contact = Contact.objects.create(
                full_name=serializer.validated_data["full_name"],
                email=serializer.validated_data["email"],
                subject=serializer.validated_data["subject"],
                message=serializer.validated_data["message"],
            )
            
            return Response(
                {
                    "status": True,
                    "message": "Your message has been sent successfully. We will get back to you soon.",
                    "data": {
                        "id": contact.id,
                        "full_name": contact.full_name,
                        "email": contact.email,
                    },
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class GenExampleView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Skip token validation

    def get(self, request):
        try:
            examples = GenExample.objects.all()
            serializer = GenExampleSerializer(examples, many=True)
            return Response(
                {
                    "status": True,
                    "message": "Generation examples retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )