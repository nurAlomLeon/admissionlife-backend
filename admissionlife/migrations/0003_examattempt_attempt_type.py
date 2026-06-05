from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissionlife', '0002_add_question_bank_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='examattempt',
            name='attempt_type',
            field=models.CharField(
                choices=[('OFFICIAL', 'Official'), ('PRACTICE', 'Practice')],
                db_index=True,
                default='OFFICIAL',
                max_length=10,
            ),
        ),
    ]
