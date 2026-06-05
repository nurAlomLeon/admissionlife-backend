from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import MonthlyAffairsIssue
from .serializers import (
    MonthlyAffairsIssueDetailSerializer,
    MonthlyAffairsIssueListSerializer,
)


class MonthlyAffairsIssueListView(generics.ListAPIView):
    serializer_class = MonthlyAffairsIssueListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = MonthlyAffairsIssue.objects.prefetch_related('blocks').order_by(
            '-year', '-month_number', 'source_category', '-source_created_at', '-id'
        )

        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        category = self.request.query_params.get('category')
        current_month = self.request.query_params.get('current_month')

        if current_month in {'1', 'true', 'True'}:
            today = timezone.localdate()
            queryset = queryset.filter(
                year=today.year,
                month_number=today.month,
            )

        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month_name__iexact=month)
        if category:
            queryset = queryset.filter(source_category__iexact=category)

        return queryset


class MonthlyAffairsIssueDetailView(generics.RetrieveAPIView):
    serializer_class = MonthlyAffairsIssueDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = MonthlyAffairsIssue.objects.prefetch_related('blocks').all()
