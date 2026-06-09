from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissionlife', '0007_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='banner_image',
            field=models.ImageField(blank=True, null=True, upload_to='admissionlife/batch_banners/'),
        ),
    ]
