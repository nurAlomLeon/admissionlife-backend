from rest_framework import serializers

from .models import MonthlyAffairsBlock, MonthlyAffairsIssue


class MonthlyAffairsBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyAffairsBlock
        fields = [
            'id',
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
        ]


class MonthlyAffairsIssueListSerializer(serializers.ModelSerializer):
    preview_text = serializers.SerializerMethodField()
    block_count = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyAffairsIssue
        fields = [
            'id',
            'source_category',
            'year',
            'month_name',
            'month_number',
            'title',
            'subtitle_category',
            'subtitle_month_label',
            'embed_url',
            'preview_text',
            'block_count',
            'scraped_at',
        ]

    def get_preview_text(self, obj):
        preview_block = obj.blocks.filter(
            block_type__in=[
                MonthlyAffairsBlock.BlockType.BULLET,
                MonthlyAffairsBlock.BlockType.PARAGRAPH,
            ]
        ).order_by('order').first()
        if preview_block is None:
            return ''
        return preview_block.text[:220]

    def get_block_count(self, obj):
        return obj.blocks.count()


class MonthlyAffairsIssueDetailSerializer(MonthlyAffairsIssueListSerializer):
    blocks = MonthlyAffairsBlockSerializer(many=True, read_only=True)

    class Meta(MonthlyAffairsIssueListSerializer.Meta):
        fields = MonthlyAffairsIssueListSerializer.Meta.fields + [
            'source_created_at',
            'source_url',
            'blocks',
        ]
