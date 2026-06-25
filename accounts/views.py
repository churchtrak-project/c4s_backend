from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .serializers import ChurchSignupSerializer, LoginSerializer, UserProfileSerializer


class ChurchSignupView(APIView):
    """
    Public self-service church onboarding.
    POST /api/auth/church-signup/
    Body: see ChurchSignupSerializer
    Returns basic success + identifiers so frontend can redirect to login or first campaign.
    """
    authentication_classes = []
    permission_classes = []   # intentionally public

    def post(self, request):
        serializer = ChurchSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            'success': True,
            'message': 'Church onboarded successfully. Admin can now log in with their phone number.',
            'church': {
                'id': result['church'].id,
                'name': result['church'].name,
                'slug': result['church'].slug,
            },
            'admin_phone': result['admin_user'].phone,
            'pastor': result['pastor'].full_name,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Role-aware login supporting the full frontend (email or phone + password).
    Returns DRF Token + user profile shaped for frontend (id, name, email, role, church, initials).
    POST /api/auth/login/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Ensure token exists (create if first login)
        token, _ = Token.objects.get_or_create(user=user)

        profile = UserProfileSerializer(user).data

        return Response({
            'token': token.key,
            'user': profile,
        }, status=status.HTTP_200_OK)