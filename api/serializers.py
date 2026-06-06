# serializers.py - Complete File with Guest User Support

from rest_framework import serializers
from .models import *

class HomeBannerNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBannerNotification
        fields = ['id', 'title', 'subtitle', 'button_text', 'batch_id', 'is_active']

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'level', 'order', 'parent', 'parent_name', 'full_path', 'question_count', 'children']
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True, context=self.context).data
        return []
    
    def get_question_count(self, obj):
        if obj.is_leaf():
            return obj.questions.count()
        else:
            descendant_ids = [desc.id for desc in obj.get_descendants() if desc.is_leaf()]
            return Question.objects.filter(category_id__in=descendant_ids).count()

class CategoryTreeSerializer(serializers.ModelSerializer):
    """Optimized serializer for tree view"""
    children = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'level', 'order', 'question_count', 'children']
    
    def get_children(self, obj):
        children = obj.children.all()
        return CategoryTreeSerializer(children, many=True, context=self.context).data
    
    def get_question_count(self, obj):
        if obj.is_leaf():
            return obj.questions.count()
        else:
            descendant_ids = [desc.id for desc in obj.get_descendants() if desc.is_leaf()]
            return Question.objects.filter(category_id__in=descendant_ids).count()

class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name']

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text', 'image', 'is_correct']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    labels = LabelSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_path = serializers.CharField(source='category.get_full_path', read_only=True, allow_null=True)
    is_saved = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_image', 'explanation', 
            'explanation_image', 'category', 'category_path', 'labels', 
            'label', 'answers', 'is_saved'
        ]

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Check if user is authenticated (regular user)
            if request.user.is_authenticated and not getattr(request.user, 'is_guest', False):
                return SavedQuestion.objects.filter(user=request.user, question=obj).exists()
            # Check if guest user
            elif getattr(request.user, 'is_guest', False):
                return SavedQuestion.objects.filter(guest_user=request.user.guest_user, question=obj).exists()
        return False
        
    def get_label(self, obj):
        if not obj.labels.exists():
            return ""
        
        label_names = [label.name for label in obj.labels.all()]
        return ", ".join(label_names)

# --- GUEST USER SERIALIZERS ---
class GuestUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestUser
        fields = ['guest_id', 'device_id', 'total_questions_answered', 'total_quizzes_completed', 'created_at', 'last_active']
        read_only_fields = ['guest_id', 'created_at', 'last_active']

class GuestLoginSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=255, help_text="Unique device identifier")

class ConvertGuestSerializer(serializers.Serializer):
    guest_id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)

# --- QUIZ CATEGORY SERIALIZER ---
class QuizCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizCategory
        fields = ['id', 'name', 'level', 'parent', 'children']
        
    def get_children(self, obj):
        if obj.children.exists():
            return QuizCategorySerializer(obj.children.all(), many=True, context=self.context).data
        return []

# --- QUIZ SERIALIZERS ---
class QuizSerializer(serializers.ModelSerializer):
    category = QuizCategorySerializer(read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'name', 'category', 'quiz_type', 'duration_minutes']

class QuizDetailSerializer(QuizSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(QuizSerializer.Meta):
        fields = QuizSerializer.Meta.fields + ['questions']

class SavedQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    question_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SavedQuestion
        fields = ['id', 'question', 'question_id', 'saved_at']
        read_only_fields = ['id', 'saved_at', 'question']

class QuestionReportSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField()

    class Meta:
        model = QuestionReport
        fields = ['id', 'question_id', 'reason', 'status', 'reported_at']
        read_only_fields = ['id', 'status', 'reported_at']

class UserSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubmission
        fields = ['question', 'selected_answer']

class QuizResultSubmissionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_answer_id = serializers.IntegerField(source='selected_answer.id', allow_null=True)

    class Meta:
        model = UserSubmission
        fields = ['question', 'selected_answer_id', 'is_correct']

class QuizAttemptResultSerializer(serializers.ModelSerializer):
    quiz = QuizDetailSerializer(read_only=True)
    submissions = QuizResultSubmissionSerializer(many=True, read_only=True)
    
    # Fields for detailed statistics
    total_questions = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    wrong_answers = serializers.SerializerMethodField()
    unanswered = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    attempted_string = serializers.SerializerMethodField(method_name='get_attempted_stat')

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'user', 'guest_user', 'quiz', 'score',
            'total_questions', 'correct_answers', 'wrong_answers', 'unanswered', 'accuracy', 'attempted_string',
            'is_completed', 'start_time', 'end_time', 'submissions'
        ]

    def get_total_questions(self, obj):
        return obj.quiz.questions.count()

    def get_correct_answers(self, obj):
        return obj.score

    def get_wrong_answers(self, obj):
        attempted_count = obj.submissions.count()
        return attempted_count - obj.score

    def get_unanswered(self, obj):
        total_questions = obj.quiz.questions.count()
        attempted_count = obj.submissions.count()
        return total_questions - attempted_count

    def get_accuracy(self, obj):
        attempted_count = obj.submissions.count()
        if attempted_count == 0:
            return 0.0
        accuracy_percent = (obj.score / attempted_count) * 100
        return round(accuracy_percent, 2)

    def get_attempted_stat(self, obj):
        total_questions = obj.quiz.questions.count()
        attempted_count = obj.submissions.count()
        return f"{attempted_count}/{total_questions}"

# ===================================================================
# SERIALIZERS FOR DAILY TARGETS AND PROGRESS TRACKING
# ===================================================================

class DailyTargetSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = DailyTarget
        fields = ['id', 'target_type', 'target_type_display', 'target_value', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DailyProgressSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = DailyProgress
        fields = [
            'id', 'target_type', 'target_type_display', 'date', 'current_value', 
            'target_value', 'is_completed', 'completion_percentage'
        ]
        read_only_fields = ['id', 'completion_percentage', 'is_completed']

class WeeklyProgressSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = WeeklyProgress
        fields = [
            'id', 'week_start_date', 'target_type', 'target_type_display', 
            'total_target', 'total_achieved', 'days_completed', 'completion_percentage'
        ]

class UserActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True, allow_null=True)
    quiz_name = serializers.CharField(source='quiz_attempt.quiz.name', read_only=True, allow_null=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'activity_type_display', 'activity_date', 'activity_time',
            'duration_minutes', 'points_earned', 'question_text', 'quiz_name'
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

class ProgressDashboardSerializer(serializers.Serializer):
    """Comprehensive serializer for dashboard data"""
    today_progress = DailyProgressSerializer(many=True, read_only=True)
    weekly_progress = WeeklyProgressSerializer(many=True, read_only=True)
    streaks = StreakSerializer(many=True, read_only=True)
    recent_activities = UserActivitySerializer(many=True, read_only=True)
    targets = DailyTargetSerializer(many=True, read_only=True)
    
    # Summary statistics
    total_questions_solved_today = serializers.IntegerField(read_only=True)
    total_quizzes_completed_today = serializers.IntegerField(read_only=True)
    total_study_time_today = serializers.IntegerField(read_only=True)  # in minutes
    
    # Weekly statistics
    weekly_questions_solved = serializers.IntegerField(read_only=True)
    weekly_quizzes_completed = serializers.IntegerField(read_only=True)
    weekly_study_time = serializers.IntegerField(read_only=True)  # in minutes

# Additional serializers for more detailed responses

class DailyProgressDetailSerializer(DailyProgressSerializer):
    """Extended daily progress serializer with additional details"""
    target_info = DailyTargetSerializer(source='user.daily_targets', read_only=True)
    progress_percentage_text = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    
    class Meta(DailyProgressSerializer.Meta):
        fields = DailyProgressSerializer.Meta.fields + [
            'target_info', 'progress_percentage_text', 'status_text'
        ]
    
    def get_progress_percentage_text(self, obj):
        return f"{obj.completion_percentage:.1f}%"
    
    def get_status_text(self, obj):
        if obj.is_completed:
            return "Completed ✅"
        elif obj.completion_percentage >= 50:
            return "In Progress 🔄"
        else:
            return "Not Started ⏳"

class WeeklyProgressDetailSerializer(WeeklyProgressSerializer):
    """Extended weekly progress serializer with additional details"""
    average_daily_completion = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta(WeeklyProgressSerializer.Meta):
        fields = WeeklyProgressSerializer.Meta.fields + [
            'average_daily_completion', 'days_remaining'
        ]
    
    def get_average_daily_completion(self, obj):
        if obj.total_target > 0:
            return round((obj.total_achieved / obj.total_target) * 100 / 7, 1)
        return 0.0
    
    def get_days_remaining(self, obj):
        from datetime import date, timedelta
        today = date.today()
        week_end = obj.week_start_date + timedelta(days=6)
        if today <= week_end:
            return (week_end - today).days + 1
        return 0

class StreakDetailSerializer(StreakSerializer):
    """Extended streak serializer with motivational messages"""
    streak_message = serializers.SerializerMethodField()
    next_milestone = serializers.SerializerMethodField()
    
    class Meta(StreakSerializer.Meta):
        fields = StreakSerializer.Meta.fields + ['streak_message', 'next_milestone']
    
    def get_streak_message(self, obj):
        streak = obj.current_streak
        if streak == 0:
            return "Start your streak today! 🚀"
        elif streak == 1:
            return "Great start! Keep it up! 💪"
        elif streak < 7:
            return f"Building momentum! {streak} days strong! 🔥"
        elif streak < 30:
            return f"Amazing consistency! {streak} day streak! 🌟"
        else:
            return f"Incredible dedication! {streak} days! You're unstoppable! 🏆"
    
    def get_next_milestone(self, obj):
        streak = obj.current_streak
        if streak < 7:
            return 7
        elif streak < 30:
            return 30
        elif streak < 100:
            return 100
        else:
            return ((streak // 50) + 1) * 50

# ===================================================================
# GUEST USER SPECIFIC SERIALIZERS
# ===================================================================

class GuestUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestUser
        fields = ['guest_id', 'device_id', 'total_questions_answered', 'total_quizzes_completed', 'created_at', 'last_active']
        read_only_fields = ['guest_id', 'created_at', 'last_active']

class GuestLoginSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=255, help_text="Unique device identifier")

class ConvertGuestSerializer(serializers.Serializer):
    guest_id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)

# ===================================================================
# ENHANCED SERIALIZERS FOR GUEST/USER COMPATIBILITY
# ===================================================================

class UniversalDailyTargetSerializer(serializers.ModelSerializer):
    """Serializer that works for both regular users and guest users"""
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyTarget
        fields = ['id', 'target_type', 'target_type_display', 'target_value', 'is_active', 'created_at', 'updated_at', 'user_type']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_type']
    
    def get_user_type(self, obj):
        return 'guest' if obj.guest_user else 'registered'

class UniversalDailyProgressSerializer(serializers.ModelSerializer):
    """Serializer that works for both regular users and guest users"""
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyProgress
        fields = [
            'id', 'target_type', 'target_type_display', 'date', 'current_value', 
            'target_value', 'is_completed', 'completion_percentage', 'user_type'
        ]
        read_only_fields = ['id', 'completion_percentage', 'is_completed', 'user_type']
    
    def get_user_type(self, obj):
        return 'guest' if obj.guest_user else 'registered'

class UniversalStreakSerializer(serializers.ModelSerializer):
    """Serializer that works for both regular users and guest users"""
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Streak
        fields = [
            'id', 'target_type', 'target_type_display', 'current_streak', 
            'longest_streak', 'last_activity_date', 'user_type'
        ]
        read_only_fields = ['user_type']
    
    def get_user_type(self, obj):
        return 'guest' if obj.guest_user else 'registered'

class UniversalUserActivitySerializer(serializers.ModelSerializer):
    """Serializer that works for both regular users and guest users"""
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True, allow_null=True)
    quiz_name = serializers.CharField(source='quiz_attempt.quiz.name', read_only=True, allow_null=True)
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'activity_type_display', 'activity_date', 'activity_time',
            'duration_minutes', 'points_earned', 'question_text', 'quiz_name', 'user_type'
        ]
        read_only_fields = ['id', 'activity_date', 'activity_time', 'user_type']
    
    def get_user_type(self, obj):
        return 'guest' if obj.guest_user else 'registered'

# ===================================================================
# UNIVERSAL DASHBOARD SERIALIZER
# ===================================================================

class UniversalProgressDashboardSerializer(serializers.Serializer):
    """Comprehensive serializer for dashboard data that works for both user types"""
    today_progress = UniversalDailyProgressSerializer(many=True, read_only=True)
    weekly_progress = WeeklyProgressSerializer(many=True, read_only=True)
    streaks = UniversalStreakSerializer(many=True, read_only=True)
    recent_activities = UniversalUserActivitySerializer(many=True, read_only=True)
    targets = UniversalDailyTargetSerializer(many=True, read_only=True)
    
    # Summary statistics
    total_questions_solved_today = serializers.IntegerField(read_only=True)
    total_quizzes_completed_today = serializers.IntegerField(read_only=True)
    total_study_time_today = serializers.IntegerField(read_only=True)  # in minutes
    
    # Weekly statistics
    weekly_questions_solved = serializers.IntegerField(read_only=True)
    weekly_quizzes_completed = serializers.IntegerField(read_only=True)
    weekly_study_time = serializers.IntegerField(read_only=True)  # in minutes
    
    # User type information
    user_type = serializers.CharField(read_only=True)
    user_identifier = serializers.CharField(read_only=True)

# ===================================================================
# ENHANCED SAVED QUESTION SERIALIZER FOR GUEST SUPPORT
# ===================================================================

class UniversalSavedQuestionSerializer(serializers.ModelSerializer):
    """Serializer that works for both regular users and guest users"""
    question = QuestionSerializer(read_only=True)
    question_id = serializers.IntegerField(write_only=True)
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = SavedQuestion
        fields = ['id', 'question', 'question_id', 'saved_at', 'user_type']
        read_only_fields = ['id', 'saved_at', 'question', 'user_type']
    
    def get_user_type(self, obj):
        return 'guest' if obj.guest_user else 'registered'