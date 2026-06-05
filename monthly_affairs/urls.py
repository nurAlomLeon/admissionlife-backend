from django.urls import path

from .views import MonthlyAffairsIssueDetailView, MonthlyAffairsIssueListView


urlpatterns = [
    path('issues/', MonthlyAffairsIssueListView.as_view(), name='monthly-affairs-issue-list'),
    path('issues/<int:pk>/', MonthlyAffairsIssueDetailView.as_view(), name='monthly-affairs-issue-detail'),
]
