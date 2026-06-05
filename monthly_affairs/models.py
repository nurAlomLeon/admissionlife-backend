from django.db import models


class MonthlyAffairsIssue(models.Model):
    source_category = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    month_name = models.CharField(max_length=20)
    month_number = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    subtitle_category = models.CharField(max_length=100, blank=True, default='')
    subtitle_month_label = models.CharField(max_length=50, blank=True, default='')
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_url = models.URLField()
    embed_url = models.URLField(blank=True, default='')
    content_hash = models.CharField(max_length=64)
    raw_html = models.TextField(blank=True, default='')
    scraped_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month_number', 'source_category']
        constraints = [
            models.UniqueConstraint(
                fields=['source_category', 'year', 'month_name'],
                name='unique_monthly_affairs_issue',
            ),
        ]
        indexes = [
            models.Index(fields=['source_category', 'year', 'month_number']),
        ]

    def __str__(self):
        return f'{self.source_category} - {self.month_name} {self.year}'


class MonthlyAffairsBlock(models.Model):
    class BlockType(models.TextChoices):
        HEADING = 'HEADING', 'Heading'
        DATE = 'DATE', 'Date'
        BULLET = 'BULLET', 'Bullet'
        PARAGRAPH = 'PARAGRAPH', 'Paragraph'
        TABLE = 'TABLE', 'Table'
        EMBED = 'EMBED', 'Embed'
        IMAGE = 'IMAGE', 'Image'

    issue = models.ForeignKey(
        MonthlyAffairsIssue,
        on_delete=models.CASCADE,
        related_name='blocks',
    )
    order = models.PositiveIntegerField()
    block_type = models.CharField(max_length=20, choices=BlockType.choices)
    heading_level = models.PositiveSmallIntegerField(null=True, blank=True)
    section_heading = models.CharField(max_length=255, blank=True, default='')
    title = models.CharField(max_length=500, blank=True, default='')
    text = models.TextField(blank=True, default='')
    event_date = models.DateField(null=True, blank=True)
    table_data = models.JSONField(null=True, blank=True)
    media_url = models.URLField(blank=True, default='')
    metadata = models.JSONField(blank=True, default=dict)
    raw_html = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=['issue', 'order'],
                name='unique_monthly_affairs_block_order',
            ),
        ]
        indexes = [
            models.Index(fields=['issue', 'block_type']),
            models.Index(fields=['event_date']),
        ]

    def __str__(self):
        return f'{self.issue} [{self.order}] {self.block_type}'
