from django.db import migrations
from django.utils import timezone


def backfill_approved_payment_enrollments(apps, schema_editor):
    Payment = apps.get_model('admissionlife', 'Payment')
    Enrollment = apps.get_model('admissionlife', 'Enrollment')

    approved_payments = Payment.objects.filter(status='APPROVED')
    for payment in approved_payments.iterator():
        enrollment, created = Enrollment.objects.get_or_create(
            user_id=payment.user_id,
            batch_id=payment.batch_id,
            defaults={'payment_id': payment.id},
        )
        if not created and enrollment.payment_id is None:
            enrollment.payment_id = payment.id
            enrollment.save(update_fields=['payment'])

        if payment.reviewed_at is None:
            payment.reviewed_at = timezone.now()
            payment.save(update_fields=['reviewed_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('admissionlife', '0008_batch_banner_image'),
    ]

    operations = [
        migrations.RunPython(
            backfill_approved_payment_enrollments,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
