import os

base = os.path.dirname(__file__)

# === 1. Update serializers.py ===
with open(os.path.join(base, 'serializers.py'), 'r', encoding='utf-8') as f:
    content = f.read()

# Add UserProfile to model imports
content = content.replace(
    "    UniversityAnswer, UniversityCategory, UniversityQuestion,\n)",
    "    UniversityAnswer, UniversityCategory, UniversityQuestion, UserProfile,\n)"
)

# Add UserProfileSerializer and CustomUserDetailsSerializer at end
extra = '''
from django.contrib.auth.models import User as DjangoUser


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['hsc_year', 'mobile_number', 'college_name', 'address']


class CustomUserDetailsSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = DjangoUser
        fields = ['pk', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['pk', 'username', 'email']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['hsc_year', 'mobile_number', 'college_name', 'address']

    def validate_mobile_number(self, value):
        if value and (len(value) != 11 or not value.startswith('01')):
            raise serializers.ValidationError(
                'Mobile number must be 11 digits starting with 01.'
            )
        return value
'''
with open(os.path.join(base, 'serializers.py'), 'w', encoding='utf-8') as f:
    f.write(content + extra)

print('SERIALIZERS PATCHED')

# === 2. Update views.py ===
with open(os.path.join(base, 'views.py'), 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
content = content.replace(
    "    UniversityCategory, UniversityQuestion,\n)",
    "    UniversityCategory, UniversityQuestion, UserProfile,\n)"
)

# Add ProfileUpdateSerializer to serializer imports
content = content.replace(
    "from .serializers import (",
    "from .serializers import (\n    ProfileUpdateSerializer,"
)

# Add view at end
view_code = '''

class ProfileUpdateView(APIView):
    """Update the authenticated user's profile fields."""

    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
'''
with open(os.path.join(base, 'views.py'), 'w', encoding='utf-8') as f:
    f.write(content + view_code)

print('VIEWS PATCHED')

# === 3. Update urls.py ===
with open(os.path.join(base, 'urls.py'), 'r', encoding='utf-8') as f:
    content = f.read()

# Add ProfileUpdateView to import
content = content.replace(
    'from .views import (',
    'from .views import (\n    ProfileUpdateView,'
)

# Add route
content = content.replace(
    '    # Practice quiz endpoints',
    '    # Profile endpoint\n    path(\n        \'profile/\',\n        ProfileUpdateView.as_view(),\n        name=\'profile-update\',\n    ),\n\n    # Practice quiz endpoints'
)

with open(os.path.join(base, 'urls.py'), 'w', encoding='utf-8') as f:
    f.write(content)

print('URLS PATCHED')

# === 4. Update settings.py ===
settings_path = os.path.join(base, '..', 'exam_project', 'settings.py')
with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "'REGISTER_SERIALIZER': 'dj_rest_auth.registration.serializers.RegisterSerializer'",
    "'REGISTER_SERIALIZER': 'dj_rest_auth.registration.serializers.RegisterSerializer',\n    'USER_DETAILS_SERIALIZER': 'admissionlife.serializers.CustomUserDetailsSerializer'"
)

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('SETTINGS PATCHED')
print('ALL DONE')
