from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='MonthlyAffairsIssue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_category', models.CharField(max_length=50)),
                ('year', models.PositiveIntegerField()),
                ('month_name', models.CharField(max_length=20)),
                ('month_number', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('title', models.CharField(max_length=255)),
                ('subtitle_category', models.CharField(blank=True, default='', max_length=100)),
                ('subtitle_month_label', models.CharField(blank=True, default='', max_length=50)),
                ('source_created_at', models.DateTimeField(blank=True, null=True)),
                ('source_url', models.URLField()),
                ('embed_url', models.URLField(blank=True, default='')),
                ('content_hash', models.CharField(max_length=64)),
                ('raw_html', models.TextField(blank=True, default='')),
                ('scraped_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-year', '-month_number', 'source_category'],
            },
        ),
        migrations.CreateModel(
            name='MonthlyAffairsBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('block_type', models.CharField(choices=[('HEADING', 'Heading'), ('DATE', 'Date'), ('BULLET', 'Bullet'), ('PARAGRAPH', 'Paragraph'), ('TABLE', 'Table'), ('EMBED', 'Embed'), ('IMAGE', 'Image')], max_length=20)),
                ('heading_level', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('section_heading', models.CharField(blank=True, default='', max_length=255)),
                ('title', models.CharField(blank=True, default='', max_length=500)),
                ('text', models.TextField(blank=True, default='')),
                ('event_date', models.DateField(blank=True, null=True)),
                ('table_data', models.JSONField(blank=True, null=True)),
                ('media_url', models.URLField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('raw_html', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('issue', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='blocks', to='monthly_affairs.monthlyaffairsissue')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.AddConstraint(
            model_name='monthlyaffairsissue',
            constraint=models.UniqueConstraint(fields=('source_category', 'year', 'month_name'), name='unique_monthly_affairs_issue'),
        ),
        migrations.AddConstraint(
            model_name='monthlyaffairsblock',
            constraint=models.UniqueConstraint(fields=('issue', 'order'), name='unique_monthly_affairs_block_order'),
        ),
        migrations.AddIndex(
            model_name='monthlyaffairsissue',
            index=models.Index(fields=['source_category', 'year', 'month_number'], name='monthly_aff_issue_idx'),
        ),
        migrations.AddIndex(
            model_name='monthlyaffairsblock',
            index=models.Index(fields=['issue', 'block_type'], name='monthly_aff_block_idx'),
        ),
        migrations.AddIndex(
            model_name='monthlyaffairsblock',
            index=models.Index(fields=['event_date'], name='monthly_aff_date_idx'),
        ),
    ]
