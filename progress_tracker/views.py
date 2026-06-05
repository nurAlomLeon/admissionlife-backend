from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from .models import DailyTarget, DailyProgress, WeeklyProgress, UserActivity, Streak
from .serializers import (
    DailyTargetSerializer, DailyProgressSerializer, WeeklyProgressSerializer,
    UserActivitySerializer, StreakSerializer
)
from api.models import GuestUser
from api.authentication import FlexibleAuthentication

class DailyTargetViewSet(viewsets.ModelViewSet):
    serializer_class = DailyTargetSerializer
    authentication_classes = [FlexibleAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'guest_user'):
            return DailyTarget.objects.filter(guest_user=user.guest_user)
        return DailyTarget.objects.filter(user=user)

class DailyProgressViewSet(viewsets.ModelViewSet):
    serializer_class = DailyProgressSerializer
    authentication_classes = [FlexibleAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'guest_user'):
            return DailyProgress.objects.filter(guest_user=user.guest_user)
        return DailyProgress.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's progress"""
        user = request.user
        today = date.today()
        
        if hasattr(user, 'guest_user'):
            progress = DailyProgress.objects.filter(guest_user=user.guest_user, date=today)
        else:
            progress = DailyProgress.objects.filter(user=user, date=today)
        
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)

class WeeklyProgressViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WeeklyProgressSerializer
    authentication_classes = [FlexibleAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'guest_user'):
            return WeeklyProgress.objects.filter(guest_user=user.guest_user)
        return WeeklyProgress.objects.filter(user=user)

class UserActivityViewSet(viewsets.ModelViewSet):
    serializer_class = UserActivitySerializer
    authentication_classes = [FlexibleAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'guest_user'):
            return UserActivity.objects.filter(guest_user=user.guest_user)
        return UserActivity.objects.filter(user=user)

class StreakViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StreakSerializer
    authentication_classes = [FlexibleAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'guest_user'):
            return Streak.objects.filter(guest_user=user.guest_user)
        return Streak.objects.filter(user=user)
