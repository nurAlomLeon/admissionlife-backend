from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Clean up orphaned SocialAccount records for this provider/uid
        orphaned = SocialAccount.objects.filter(
            provider=sociallogin.account.provider,
            uid=sociallogin.account.uid,
            user__isnull=True
        )
        if orphaned.exists():
            orphaned.delete()

        # Connect to existing user if email matches
        email = user_email(sociallogin.user)

        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)

                if not SocialAccount.objects.filter(
                    user=existing_user,
                    provider=sociallogin.account.provider,
                    uid=sociallogin.account.uid
                ).exists():
                    sociallogin.connect(request, existing_user)

            except User.DoesNotExist:
                pass
            except User.MultipleObjectsReturned:
                existing_user = User.objects.filter(email__iexact=email).first()
                if not SocialAccount.objects.filter(
                    user=existing_user,
                    provider=sociallogin.account.provider,
                    uid=sociallogin.account.uid
                ).exists():
                    sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        # Set username before calling super().save_user() so that when
        # sociallogin.save() runs inside super, the User has a non-empty
        # username (required by Django's default User model).
        if not sociallogin.user.username or sociallogin.user.username == '':
            email = user_email(sociallogin.user)
            if email:
                base_username = email.split('@')[0]
            else:
                base_username = f"social_user_{sociallogin.account.uid}"

            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            sociallogin.user.username = username

        user = super().save_user(request, sociallogin, form)

        if sociallogin.account.provider == 'google':
            extra_data = sociallogin.account.extra_data

            # Always set first_name/last_name from authoritative Google data
            if extra_data:
                if 'given_name' in extra_data:
                    user.first_name = extra_data['given_name']
                if 'family_name' in extra_data:
                    user.last_name = extra_data['family_name']

                # Fallback: parse full name when individual fields missing
                if (not user.first_name or not user.last_name) and 'name' in extra_data:
                    name_parts = extra_data['name'].split()
                    if len(name_parts) >= 1 and not user.first_name:
                        user.first_name = name_parts[0]
                    if len(name_parts) >= 2 and not user.last_name:
                        user.last_name = ' '.join(name_parts[1:])

            # Fallback: use sociallogin.user if extra_data didn't have name
            if not user.first_name and sociallogin.user.first_name:
                user.first_name = sociallogin.user.first_name
            if not user.last_name and sociallogin.user.last_name:
                user.last_name = sociallogin.user.last_name

            user.save()

        return user
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Allow auto-signup for all Google users
        """
        # Always allow auto-signup
        return True