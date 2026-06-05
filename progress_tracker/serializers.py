from rest_framework import serializers
from .models import DailyTarget, DailyProgress, WeeklyProgress, UserActivity, Streak

class DailyTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTarget
        fields = ['id', 'target_type', 'target_value', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DailyProgressSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = DailyProgress
        fields = [
            'id', 'target_type', 'target_type_display', 'date', 'current_value', 
            'target_value', 'is_completed', 'completion_percentage'
        ]
        read_only_fields = ['id', 'is_completed', 'completion_percentage']

class WeeklyProgressSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = WeeklyProgress
        fields = [
            'id', 'target_type', 'target_type_display', 'week_start_date', 
            'total_target', 'total_achieved', 'days_completed', 'completion_percentage'
        ]
        read_only_fields = ['id']

class UserActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'activity_type_display', 'activity_date', 
            'activity_time', 'duration_minutes', 'points_earned'
        ]
        read_only_fields = ['id', 'activity_date', 'activity_time']

class StreakSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = Streak
        fields = [
            'id', 'target_type', 'target_type_display', 'current_streak', 
            'longest_streak', 'last_activity_date'
        ]
        read_only_fields = ['id', 'last_activity_date']
