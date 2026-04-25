from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import UserProfileSerializer, UserRegistrationSerializer


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={201: UserProfileSerializer},
        examples=[
            OpenApiExample(
                "Valid Registration",
                value={
                    "email": "test@example.com",
                    "full_name": "Test User",
                    "password": "securepass123",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_serializer = UserProfileSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        request=UserProfileSerializer, responses={200: UserProfileSerializer}
    )
    def patch(self, request: Request) -> Response:
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request: Request) -> Response:
        request.user.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
