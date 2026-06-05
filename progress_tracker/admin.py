from django.contrib import admin
from .models import DailyTarget, DailyProgress, WeeklyProgress, UserActivity, Streak

@admin.register(DailyTarget)
class DailyTargetAdmin(admin.ModelAdmin):
    list_display = ['get_user_identifier', 'target_type', 'target_value', 'is_active', 'created_at']
    list_filter = ['target_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'guest_user__guest_id']
    
    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.username
        return f"Guest {obj.guest_user.guest_id}"
    get_user_identifier.short_description = 'User'

@admin.register(DailyProgress)
class DailyProgressAdmin(admin.ModelAdmin):
    list_display = ['get_user_identifier', 'target_type', 'date', 'current_value', 'target_value', 'is_completed', 'completion_percentage']
    list_filter = ['target_type', 'date', 'is_completed']
    search_fields = ['user__username', 'guest_user__guest_id']
    readonly_fields = ['completion_percentage']
    
    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.username
        return f"Guest {obj.guest_user.guest_id}"
    get_user_identifier.short_description = 'User'

@admin.register(WeeklyProgress)
class WeeklyProgressAdmin(admin.ModelAdmin):
    list_display = ['get_user_identifier', 'target_type', 'week_start_date', 'total_achieved', 'total_target', 'days_completed', 'completion_percentage']
    list_filter = ['target_type', 'week_start_date']
    search_fields = ['user__username', 'guest_user__guest_id']
    
    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.username
        return f"Guest {obj.guest_user.guest_id}"
    get_user_identifier.short_description = 'User'

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['get_user_identifier', 'activity_type', 'activity_date', 'activity_time', 'duration_minutes', 'points_earned']
    list_filter = ['activity_type', 'activity_date', 'activity_time']
    search_fields = ['user__username', 'guest_user__guest_id']
    readonly_fields = ['activity_date', 'activity_time']
    
    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.username
        return f"Guest {obj.guest_user.guest_id}"
    get_user_identifier.short_description = 'User'

@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    list_display = ['get_user_identifier', 'target_type', 'current_streak', 'longest_streak', 'last_activity_date']
    list_filter = ['target_type', 'last_activity_date']
    search_fields = ['user__username', 'guest_user__guest_id']
    readonly_fields = ['last_activity_date']
    
    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.username
        return f"Guest {obj.guest_user.guest_id}"
    get_user_identifier.short_description = 'User'
