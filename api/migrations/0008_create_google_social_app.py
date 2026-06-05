from django.conf import settings
from django.db import migrations


def create_google_social_app(apps, schema_editor):
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    Site = apps.get_model('sites', 'Site')

    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
    secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')

    if not client_id:
        return

    site, created = Site.objects.get_or_create(
        id=settings.SITE_ID,
        defaults={
            'domain': 'admission.mcqsolver.com',
            'name': 'Admission Life',
        },
    )
    if created:
        print(f"Created site with id={settings.SITE_ID}")

    app, created = SocialApp.objects.get_or_create(
        provider='google',
        client_id=client_id,
        defaults={
            'name': 'Google',
            'secret': secret,
            'key': '',
        },
    )

    # Ensure the app is associated with the site
    if not app.sites.filter(id=site.id).exists():
        app.sites.add(site)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_guestuser_quizcategory_streak_useractivity_and_more'),
        ('sites', '0002_alter_domain_unique'),
        ('socialaccount', '0006_alter_socialaccount_extra_data'),
    ]

    operations = [
        migrations.RunPython(create_google_social_app, migrations.RunPython.noop),
    ]
