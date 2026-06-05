from django.contrib import admin

from .models import MonthlyAffairsBlock, MonthlyAffairsIssue


class MonthlyAffairsBlockInline(admin.StackedInline):
    model = MonthlyAffairsBlock
    extra = 0
    ordering = ['order']
    readonly_fields = (
        'order',
        'block_type',
        'heading_level',
        'section_heading',
        'title',
        'text',
        'event_date',
        'table_data',
        'media_url',
        'metadata',
        'raw_html',
        'created_at',
    )
    can_delete = False


@admin.register(MonthlyAffairsIssue)
class MonthlyAffairsIssueAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'source_category',
        'month_name',
        'year',
        'month_number',
        'block_count',
        'scraped_at',
    )
    list_filter = ('source_category', 'year', 'month_name')
    search_fields = ('title', 'subtitle_category', 'subtitle_month_label')
    readonly_fields = (
        'source_category',
        'year',
        'month_name',
        'month_number',
        'title',
        'subtitle_category',
        'subtitle_month_label',
        'source_created_at',
        'source_url',
        'embed_url',
        'content_hash',
        'raw_html',
        'scraped_at',
        'created_at',
        'updated_at',
    )
    inlines = [MonthlyAffairsBlockInline]

    def block_count(self, obj):
        return obj.blocks.count()

    block_count.short_description = 'Blocks'
