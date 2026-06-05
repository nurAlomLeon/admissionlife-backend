from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from api.models import GuestUser, Question, QuizAttempt

class DailyTarget(models.Model):
    """Model to store user's daily targets"""
    
    class TargetType(models.TextChoices):
        QUESTIONS_SOLVED = 'QUESTIONS_SOLVED', 'Questions Solved'
        MODEL_TESTS_TAKEN = 'MODEL_TESTS_TAKEN', 'Model Tests Taken'
        PRACTICE_TIME_MINUTES = 'PRACTICE_TIME_MINUTES', 'Practice Time (Minutes)'
        QUIZ_ATTEMPTS = 'QUIZ_ATTEMPTS', 'Quiz Attempts'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_targets', null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, related_name='daily_targets', null=True, blank=True)
    target_type = models.CharField(max_length=30, choices=TargetType.choices)
    target_value = models.PositiveIntegerField(help_text="Target value (e.g., 50 questions, 2 tests, 120 minutes)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_user__isnull=False),
                name='progress_daily_target_must_have_user_or_guest'
            ),
            models.CheckConstraint(
                check=~(models.Q(user__isnull=False) & models.Q(guest_user__isnull=False)),
                name='progress_daily_target_cannot_have_both_user_and_guest'
            ),
            models.UniqueConstraint(
                fields=['user', 'target_type'], 
                condition=models.Q(user__isnull=False),
                name='progress_unique_user_target_type'
            ),
            models.UniqueConstraint(
                fields=['guest_user', 'target_type'], 
                condition=models.Q(guest_user__isnull=False),
                name='progress_unique_guest_target_type'
            )
        ]
        verbose_name = "Daily Target"
        verbose_name_plural = "Daily Targets"
    
    def __str__(self):
        user_identifier = str(self.user.username) if self.user else f"Guest {str(self.guest_user.guest_id)}"
        target_display = str(self.get_target_type_display())
        return f"{user_identifier} - {target_display}: {self.target_value}"

class DailyProgress(models.Model):
    """Model to track daily progress for each target"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_progress', null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, related_name='daily_progress', null=True, blank=True)
    target_type = models.CharField(max_length=30, choices=DailyTarget.TargetType.choices)
    date = models.DateField(default=date.today)
    current_value = models.PositiveIntegerField(default=0)
    target_value = models.PositiveIntegerField(help_text="Target value for this date")
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0.0)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_user__isnull=False),
                name='progress_daily_progress_must_have_user_or_guest'
            ),
            models.CheckConstraint(
                check=~(models.Q(user__isnull=False) & models.Q(guest_user__isnull=False)),
                name='progress_daily_progress_cannot_have_both_user_and_guest'
            ),
            models.UniqueConstraint(
                fields=['user', 'target_type', 'date'], 
                condition=models.Q(user__isnull=False),
                name='progress_unique_user_target_date'
            ),
            models.UniqueConstraint(
                fields=['guest_user', 'target_type', 'date'], 
                condition=models.Q(guest_user__isnull=False),
                name='progress_unique_guest_target_date'
            )
        ]
        ordering = ['-date', 'target_type']
        verbose_name = "Daily Progress"
        verbose_name_plural = "Daily Progress"
    
    def save(self, *args, **kwargs):
        # Auto-calculate completion percentage and status
        if self.target_value > 0:
            self.completion_percentage = min((self.current_value / self.target_value) * 100, 100.0)
            self.is_completed = self.current_value >= self.target_value
        super().save(*args, **kwargs)
    
    def __str__(self):
        user_identifier = str(self.user.username) if self.user else f"Guest {str(self.guest_user.guest_id)}"
        target_display = str(self.get_target_type_display())
        return f"{user_identifier} - {str(self.date)} - {target_display}: {self.current_value}/{self.target_value}"

class WeeklyProgress(models.Model):
    """Model to track weekly progress summary"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_progress', null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, related_name='weekly_progress', null=True, blank=True)
    week_start_date = models.DateField()  # Monday of the week
    target_type = models.CharField(max_length=30, choices=DailyTarget.TargetType.choices)
    total_target = models.PositiveIntegerField(default=0)
    total_achieved = models.PositiveIntegerField(default=0)
    days_completed = models.PositiveIntegerField(default=0)  # Number of days target was met
    completion_percentage = models.FloatField(default=0.0)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_user__isnull=False),
                name='progress_weekly_progress_must_have_user_or_guest'
            ),
            models.CheckConstraint(
                check=~(models.Q(user__isnull=False) & models.Q(guest_user__isnull=False)),
                name='progress_weekly_progress_cannot_have_both_user_and_guest'
            ),
            models.UniqueConstraint(
                fields=['user', 'week_start_date', 'target_type'], 
                condition=models.Q(user__isnull=False),
                name='progress_unique_user_week_target'
            ),
            models.UniqueConstraint(
                fields=['guest_user', 'week_start_date', 'target_type'], 
                condition=models.Q(guest_user__isnull=False),
                name='progress_unique_guest_week_target'
            )
        ]
        ordering = ['-week_start_date', 'target_type']
        verbose_name = "Weekly Progress"
        verbose_name_plural = "Weekly Progress"
    
    def __str__(self):
        user_identifier = str(self.user.username) if self.user else f"Guest {str(self.guest_user.guest_id)}"
        target_display = str(self.get_target_type_display())
        return f"{user_identifier} - Week of {str(self.week_start_date)} - {target_display}"

class UserActivity(models.Model):
    """Model to log user activities for progress tracking"""
    
    class ActivityType(models.TextChoices):
        QUESTION_ANSWERED = 'QUESTION_ANSWERED', 'Question Answered'
        QUIZ_COMPLETED = 'QUIZ_COMPLETED', 'Quiz Completed'
        MODEL_TEST_COMPLETED = 'MODEL_TEST_COMPLETED', 'Model Test Completed'
        PRACTICE_SESSION = 'PRACTICE_SESSION', 'Practice Session'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    activity_date = models.DateField(auto_now_add=True)
    activity_time = models.DateTimeField(auto_now_add=True)
    
    # Optional references to related objects
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, null=True, blank=True)
    
    # Additional metadata
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Duration of activity in minutes")
    points_earned = models.PositiveIntegerField(default=0)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_user__isnull=False),
                name='progress_user_activity_must_have_user_or_guest'
            ),
            models.CheckConstraint(
                check=~(models.Q(user__isnull=False) & models.Q(guest_user__isnull=False)),
                name='progress_user_activity_cannot_have_both_user_and_guest'
            )
        ]
        ordering = ['-activity_time']
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
    
    def __str__(self):
        user_identifier = str(self.user.username) if self.user else f"Guest {str(self.guest_user.guest_id)}"
        activity_display = str(self.get_activity_type_display())
        return f"{user_identifier} - {activity_display} on {str(self.activity_date)}"

class Streak(models.Model):
    """Model to track user streaks for different activities"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streaks', null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, related_name='streaks', null=True, blank=True)
    target_type = models.CharField(max_length=30, choices=DailyTarget.TargetType.choices)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_user__isnull=False),
                name='progress_streak_must_have_user_or_guest'
            ),
            models.CheckConstraint(
                check=~(models.Q(user__isnull=False) & models.Q(guest_user__isnull=False)),
                name='progress_streak_cannot_have_both_user_and_guest'
            ),
            models.UniqueConstraint(
                fields=['user', 'target_type'], 
                condition=models.Q(user__isnull=False),
                name='progress_unique_user_streak_type'
            ),
            models.UniqueConstraint(
                fields=['guest_user', 'target_type'], 
                condition=models.Q(guest_user__isnull=False),
                name='progress_unique_guest_streak_type'
            )
        ]
        verbose_name = "Streak"
        verbose_name_plural = "Streaks"
    
    def update_streak(self, activity_date=None):
        """Update streak based on activity date"""
        if activity_date is None:
            activity_date = date.today()
        
        if self.last_activity_date is None:
            # First activity
            self.current_streak = 1
            self.longest_streak = 1
            self.last_activity_date = activity_date
        elif self.last_activity_date == activity_date:
            # Same day activity, don't change streak
            return
        elif self.last_activity_date == activity_date - timedelta(days=1):
            # Consecutive day
            self.current_streak += 1
            self.longest_streak = max(self.longest_streak, self.current_streak)
            self.last_activity_date = activity_date
        elif self.last_activity_date < activity_date - timedelta(days=1):
            # Streak broken
            self.current_streak = 1
            self.last_activity_date = activity_date
        
        self.save()
    
    def __str__(self):
        user_identifier = str(self.user.username) if self.user else f"Guest {str(self.guest_user.guest_id)}"
        target_display = str(self.get_target_type_display())
        return f"{user_identifier} - {target_display} - Current: {self.current_streak}, Best: {self.longest_streak}"
