from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyTargetViewSet, DailyProgressViewSet, WeeklyProgressViewSet,
    UserActivityViewSet, StreakViewSet
)

router = DefaultRouter()
router.register(r'daily-targets', DailyTargetViewSet, basename='daily-targets')
router.register(r'daily-progress', DailyProgressViewSet, basename='daily-progress')
router.register(r'weekly-progress', WeeklyProgressViewSet, basename='weekly-progress')
router.register(r'user-activities', UserActivityViewSet, basename='user-activities')
router.register(r'streaks', StreakViewSet, basename='streaks')

urlpatterns = [
    path('', include(router.urls)),
]
