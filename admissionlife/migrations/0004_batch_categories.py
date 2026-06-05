from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissionlife', '0003_examattempt_attempt_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='BatchCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='batchcategory',
            index=models.Index(fields=['order'], name='admissionli_order_605803_idx'),
        ),
        migrations.AddField(
            model_name='batch',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='batches', to='admissionlife.batchcategory'),
        ),
    ]
