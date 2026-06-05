# views.py - Complete File with Guest User Support

import random
from rest_framework import viewsets, generics, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.db import models
from .models import *
from .serializers import *
from .pagination import StandardResultsSetPagination
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from .permissions import IsAuthenticatedOrGuest, IsAuthenticatedUserOnly, GuestLimitedPermission
from .authentication import FlexibleAuthentication

# Additional imports for progress tracking
from datetime import date, timedelta, datetime
from django.db.models import Sum, Count, Q, Avg
from collections import defaultdict
from django.contrib.auth.models import User

# For Google Login
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except OAuth2Error:
            return Response(
                {'detail': 'Invalid Google access token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

# ===================================================================
# GUEST USER AUTHENTICATION VIEWS
# ===================================================================

class GuestLoginView(APIView):
    """
    Create or retrieve a guest user session
    """
    authentication_classes = []
    permission_classes = []
    
    def post(self, request):
        serializer = GuestLoginSerializer(data=request.data)
        if serializer.is_valid():
            device_id = serializer.validated_data['device_id']
            
            # Get or create guest user
            guest_user, created = GuestUser.objects.get_or_create(
                device_id=device_id
            )
            
            response_data = {
                'guest_token': str(guest_user.guest_id),
                'device_id': device_id,
                'is_new_guest': created,
                'guest_data': GuestUserSerializer(guest_user).data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ConvertGuestToUserView(APIView):
    """
    Convert a guest user to a registered user
    """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    
    def post(self, request):
        if not getattr(request.user, 'is_guest', False):
            return Response(
                {"error": "This endpoint is only for guest users"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ConvertGuestSerializer(data=request.data)
        if serializer.is_valid():
            guest_id = serializer.validated_data['guest_id']
            email = serializer.validated_data['email']
            name = serializer.validated_data['name']
            
            try:
                guest_user = GuestUser.objects.get(guest_id=guest_id)
                
                # Create new regular user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=name.split()[0] if name.split() else name,
                    last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
                )
                
                # Transfer guest data to user
                with transaction.atomic():
                    # Transfer saved questions
                    SavedQuestion.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer quiz attempts
                    QuizAttempt.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer daily targets
                    DailyTarget.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer daily progress
                    DailyProgress.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer weekly progress
                    WeeklyProgress.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer user activities
                    UserActivity.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Transfer streaks
                    Streak.objects.filter(guest_user=guest_user).update(
                        user=user, guest_user=None
                    )
                    
                    # Delete guest user record
                    guest_user.delete()
                
                return Response({
                    "message": "Guest account successfully converted to registered user",
                    "user_id": user.id,
                    "email": user.email
                }, status=status.HTTP_200_OK)
                
            except GuestUser.DoesNotExist:
                return Response(
                    {"error": "Guest user not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"error": f"Conversion failed: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ===================================================================
# UTILITY FUNCTIONS FOR GUEST/USER COMPATIBILITY
# ===================================================================

def get_user_or_guest(request):
    """Helper function to get either regular user or guest user"""
    if hasattr(request.user, 'is_guest') and request.user.is_guest:
        return None, request.user.guest_user
    elif request.user.is_authenticated and not getattr(request.user, 'is_guest', False):
        return request.user, None
    return None, None

def get_user_queryset_filter(request):
    """Helper function to get appropriate filter for user or guest"""
    user, guest_user = get_user_or_guest(request)
    if user:
        return Q(user=user)
    elif guest_user:
        return Q(guest_user=guest_user)
    return Q(pk=None)  # Return empty queryset

# ===================================================================
# MAIN VIEWSETS WITH GUEST SUPPORT
# ===================================================================

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ Provides hierarchical category structure """
    queryset = Category.objects.all().select_related('parent').prefetch_related('children')
    serializer_class = CategorySerializer
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        level = self.request.query_params.get('level')
        parent = self.request.query_params.get('parent')
        
        if level is not None:
            queryset = queryset.filter(level=level)
        if parent is not None:
            if parent == 'null' or parent == '':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get the complete category tree structure"""
        root_categories = Category.objects.filter(parent__isnull=True).prefetch_related('children__children')
        serializer = CategoryTreeSerializer(root_categories, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def subjects(self, request):
        """Get only root level categories (subjects)"""
        subjects = Category.objects.filter(level=0, parent__isnull=True)
        serializer = CategorySerializer(subjects, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def parts(self, request, pk=None):
        """Get parts (level 1) for a specific subject"""
        try:
            subject = Category.objects.get(pk=pk, level=0)
            parts = subject.children.filter(level=1)
            serializer = CategorySerializer(parts, many=True, context={'request': request})
            return Response(serializer.data)
        except Category.DoesNotExist:
            return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def topics(self, request, pk=None):
        """Get topics (level 2) for a specific part"""
        try:
            part = Category.objects.get(pk=pk, level=1)
            topics = part.children.filter(level=2)
            serializer = CategorySerializer(topics, many=True, context={'request': request})
            return Response(serializer.data)
        except Category.DoesNotExist:
            return Response({"error": "Part not found"}, status=status.HTTP_404_NOT_FOUND)

class QuizCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a hierarchical structure for Quiz Categories.
    Use ?parent=null to get root categories.
    """
    queryset = QuizCategory.objects.filter(parent__isnull=True).prefetch_related('children')
    serializer_class = QuizCategorySerializer
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get the complete quiz category tree structure."""
        root_categories = QuizCategory.objects.filter(parent__isnull=True).prefetch_related('children__children')
        serializer = QuizCategorySerializer(root_categories, many=True, context={'request': request})
        return Response(serializer.data)

class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    """ Provides read-only access to pre-defined quizzes with category and quiz type filtering """
    queryset = Quiz.objects.all().select_related('category').prefetch_related('questions__answers')
    serializer_class = QuizDetailSerializer
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Category filtering - support both 'category' and 'category_id' parameters
        category_id = self.request.query_params.get('category') or self.request.query_params.get('category_id')
        if category_id:
            try:
                queryset = queryset.filter(category__id=int(category_id))
            except (ValueError, TypeError):
                pass  # Invalid category ID, ignore filter
        
        # Quiz type filtering - for question banks specifically
        quiz_type = self.request.query_params.get('quiz_type')
        if quiz_type:
            queryset = queryset.filter(quiz_type=quiz_type)
            print(f'Filtering by quiz_type: {quiz_type}, found {queryset.count()} quizzes')
        
        # Debug: Log the quiz types being returned
        if queryset.exists():
            quiz_types = queryset.values_list('quiz_type', flat=True).distinct()
            print(f'Quiz types in result: {list(quiz_types)}')
            
        return queryset

class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """ Provides read-only access to questions with hierarchical filtering """
    queryset = Question.objects.all().select_related('category').prefetch_related('answers', 'labels')
    serializer_class = QuestionSerializer
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category')
        category_level = self.request.query_params.get('category_level')
        
        if category:
            if category_level == 'all':
                try:
                    cat = Category.objects.get(id=category)
                    if cat.is_leaf():
                        queryset = queryset.filter(category_id=category)
                    else:
                        descendant_ids = [desc.id for desc in cat.get_descendants() if desc.is_leaf()]
                        if cat.is_leaf():
                            descendant_ids.append(cat.id)
                        queryset = queryset.filter(category_id__in=descendant_ids)
                except Category.DoesNotExist:
                    queryset = queryset.none()
            else:
                queryset = queryset.filter(category__id=category)
        
        return queryset

class CreateModelTestView(APIView):
    """ Creates a custom model test based on hierarchical category selection """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]

    def post(self, request, *args, **kwargs):
        config = request.data.get('config', [])
        quiz_name = request.data.get('name', 'Custom Model Test')
        duration = request.data.get('duration_minutes', 30)
        
        if not isinstance(config, list) or not config:
            return Response({"error": "Configuration must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        final_question_ids = set()
        
        for item in config:
            try:
                category_id = item['category_id']
                count = item['count']
                include_subcategories = item.get('include_subcategories', False)
                
                category_ids_to_query = [category_id]
                if include_subcategories:
                    try:
                        category = Category.objects.get(id=category_id)
                        if not category.is_leaf():
                            descendant_ids = [desc.id for desc in category.get_descendants() if desc.is_leaf()]
                            category_ids_to_query.extend(descendant_ids)
                    except Category.DoesNotExist:
                        continue
                
                question_ids_pool = list(
                    Question.objects.filter(category_id__in=category_ids_to_query).values_list('id', flat=True)
                )

                if len(question_ids_pool) <= count:
                    selected_ids = question_ids_pool
                else:
                    selected_ids = random.sample(question_ids_pool, count)
                
                final_question_ids.update(selected_ids)
                
            except (KeyError, TypeError):
                continue

        if not final_question_ids:
            return Response({"error": "No questions found for the given configuration."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            quiz = Quiz.objects.create(
                name=quiz_name, 
                duration_minutes=duration, 
                quiz_type=Quiz.QuizType.MODEL_TEST
            )
            quiz.questions.set(list(final_question_ids))
        
        serializer = QuizDetailSerializer(quiz, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class QuizResultView(generics.RetrieveAPIView):
    """
    Provides the detailed result for a single, completed quiz attempt.
    Works for both regular users and guests.
    """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = QuizAttemptResultSerializer
    lookup_url_kwarg = 'attempt_id'

    def get_queryset(self):
        """
        Filter quiz attempts based on user type
        """
        user_filter = get_user_queryset_filter(self.request)
        return QuizAttempt.objects.filter(user_filter)

class SavedQuestionFilter(django_filters.FilterSet):
    """
    Custom filter class to handle both category and label filtering
    """
    category = django_filters.CharFilter(method='filter_by_category')
    category_id = django_filters.NumberFilter(field_name='question__category__id')
    category_name = django_filters.CharFilter(field_name='question__category__name', lookup_expr='icontains')
    label = django_filters.CharFilter(field_name='question__labels__name', lookup_expr='icontains')
    label_name = django_filters.CharFilter(field_name='question__labels__name', lookup_expr='icontains')
    question__labels__name = django_filters.CharFilter(field_name='question__labels__name', lookup_expr='icontains')
    
    class Meta:
        model = SavedQuestion
        fields = [
            'category', 'category_id', 'category_name',
            'label', 'label_name', 'question__labels__name'
        ]
    
    def filter_by_category(self, queryset, name, value):
        return queryset.filter(
            models.Q(question__category__name__icontains=value) |
            models.Q(question__labels__name__icontains=value)
        ).distinct()

class SavedQuestionViewSet(mixins.CreateModelMixin, 
                           mixins.DestroyModelMixin, 
                           mixins.ListModelMixin, 
                           viewsets.GenericViewSet):
    """ 
    Allows users to list, save (create), and unsave (delete) questions 
    with proper category and label filtering support.
    Works for both regular users and guests.
    """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = UniversalSavedQuestionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SavedQuestionFilter
    search_fields = ['question__question_text', 'question__explanation']
    ordering_fields = ['saved_at', 'question__category__name', 'question__labels__name']
    ordering = ['-saved_at']

    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        return SavedQuestion.objects.filter(user_filter).select_related(
            'question__category'
        ).prefetch_related(
            'question__labels',
            'question__answers'
        ).distinct()

    def create(self, request, *args, **kwargs):
        question_id = request.data.get('question_id')
        if not question_id:
            return Response(
                {"error": "question_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the question exists
        if not Question.objects.filter(id=question_id).exists():
            return Response(
                {"error": f"Question with id {question_id} not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        user, guest_user = get_user_or_guest(request)
        
        # Check for existing saved question
        if user:
            already_exists = SavedQuestion.objects.filter(user=user, question_id=question_id).exists()
            existing_instance = SavedQuestion.objects.filter(user=user, question_id=question_id).first()
        else:
            already_exists = SavedQuestion.objects.filter(guest_user=guest_user, question_id=question_id).exists()
            existing_instance = SavedQuestion.objects.filter(guest_user=guest_user, question_id=question_id).first()

        if already_exists:
            serializer = self.get_serializer(existing_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new saved question
        if user:
            saved_question = SavedQuestion.objects.create(user=user, question_id=question_id)
        else:
            saved_question = SavedQuestion.objects.create(guest_user=guest_user, question_id=question_id)
        
        serializer = self.get_serializer(saved_question)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='bulk-save')
    def bulk_save(self, request):
        """
        Saves multiple questions in a single API call.
        Works for both regular users and guests.
        """
        question_ids = request.data.get('question_ids')

        if not isinstance(question_ids, list):
            return Response(
                {"error": "The 'question_ids' field must be a list of integers."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user, guest_user = get_user_or_guest(request)
        
        # Filter out IDs that do not correspond to existing questions
        valid_question_ids = set(Question.objects.filter(id__in=question_ids).values_list('id', flat=True))
        
        # Find which questions are already saved
        if user:
            already_saved_ids = set(
                SavedQuestion.objects.filter(user=user, question_id__in=valid_question_ids)
                .values_list('question_id', flat=True)
            )
        else:
            already_saved_ids = set(
                SavedQuestion.objects.filter(guest_user=guest_user, question_id__in=valid_question_ids)
                .values_list('question_id', flat=True)
            )
        
        # Determine new questions to save
        ids_to_save = valid_question_ids - already_saved_ids
        
        if not ids_to_save:
            return Response({
                "status": "success",
                "message": "No new questions to save. All provided questions were either invalid or already saved.",
                "saved_count": 0,
                "already_saved_count": len(already_saved_ids)
            }, status=status.HTTP_200_OK)
            
        # Create new SavedQuestion objects
        if user:
            new_saves = [SavedQuestion(user=user, question_id=qid) for qid in ids_to_save]
        else:
            new_saves = [SavedQuestion(guest_user=guest_user, question_id=qid) for qid in ids_to_save]
        
        SavedQuestion.objects.bulk_create(new_saves)
        
        return Response({
            "status": "success",
            "message": f"Successfully processed the request.",
            "saved_count": len(new_saves),
            "already_saved_count": len(already_saved_ids)
        }, status=status.HTTP_201_CREATED)

class QuestionReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """ Allows users to report a question - only for registered users """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedUserOnly]  # Only registered users can report
    serializer_class = QuestionReportSerializer
    queryset = QuestionReport.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExamAttemptViewSet(viewsets.GenericViewSet):
    """ Handles the entire exam-taking process for both users and guests """
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    queryset = QuizAttempt.objects.all()

    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        return QuizAttempt.objects.filter(user_filter)

    @action(detail=True, methods=['post'], url_path='start')
    def start_exam(self, request, pk=None):
        try:
            quiz = Quiz.objects.get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        
        user, guest_user = get_user_or_guest(request)
        
        # Create or get quiz attempt
        if user:
            attempt, created = QuizAttempt.objects.get_or_create(
                user=user, 
                quiz=quiz, 
                is_completed=False,
                defaults={'start_time': timezone.now()}
            )
        else:
            attempt, created = QuizAttempt.objects.get_or_create(
                guest_user=guest_user, 
                quiz=quiz, 
                is_completed=False,
                defaults={'start_time': timezone.now()}
            )
        
        serializer = QuizDetailSerializer(quiz, context={'request': request})
        return Response({
            "attempt_id": attempt.id,
            "quiz_details": serializer.data
        })

    @action(detail=True, methods=['post'], url_path='submit-answer')
    def submit_answer(self, request, pk=None):
        user_filter = get_user_queryset_filter(request)
        
        try:
            attempt = QuizAttempt.objects.get(
                Q(pk=pk) & user_filter & Q(is_completed=False)
            )
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Active quiz attempt not found."}, status=status.HTTP_404_NOT_FOUND)
        
        question_id = request.data.get('question_id')
        answer_id = request.data.get('answer_id')

        try:
            question = Question.objects.get(pk=question_id)
            answer = Answer.objects.get(pk=answer_id, question=question)
        except (Question.DoesNotExist, Answer.DoesNotExist):
            return Response({"error": "Invalid question or answer ID."}, status=status.HTTP_400_BAD_REQUEST)

        is_correct = answer.is_correct
        UserSubmission.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'selected_answer': answer, 'is_correct': is_correct}
        )
        return Response({"status": "Answer submitted successfully."}, status=status.HTTP_200_OK)
        
    @action(detail=True, methods=['post'], url_path='submit-bulk')
    @transaction.atomic
    def submit_bulk_answers(self, request, pk=None):
        """
        Submits a list of answers, calculates score, and ends the exam in a single call.
        Works for both regular users and guests.
        """
        user_filter = get_user_queryset_filter(request)
        
        try:
            attempt = QuizAttempt.objects.get(
                Q(pk=pk) & user_filter & Q(is_completed=False)
            )
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Active quiz attempt not found."}, status=status.HTTP_404_NOT_FOUND)
        
        submissions_data = request.data.get('submissions', [])
        if not isinstance(submissions_data, list):
            return Response({"error": "Submissions must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all question IDs from the submission data
        question_ids = [sub.get('question_id') for sub in submissions_data if sub.get('question_id')]
        
        # Fetch all correct answers for the relevant questions in a single query
        correct_answers_map = {
            ans.question_id: ans.id 
            for ans in Answer.objects.filter(question_id__in=question_ids, is_correct=True)
        }

        # Prepare UserSubmission objects for bulk creation
        submissions_to_create = []
        for sub_data in submissions_data:
            question_id = sub_data.get('question_id')
            selected_answer_id = sub_data.get('selected_answer_id')
            
            if not question_id:
                continue

            is_correct = correct_answers_map.get(question_id) == selected_answer_id

            submissions_to_create.append(
                UserSubmission(
                    attempt=attempt,
                    question_id=question_id,
                    selected_answer_id=selected_answer_id,
                    is_correct=is_correct
                )
            )

        # Clear any previous submissions for this attempt to prevent duplicates
        UserSubmission.objects.filter(attempt=attempt).delete()
        
        # Create all new submissions in one database query
        UserSubmission.objects.bulk_create(submissions_to_create)

        # Calculate score and finalize the attempt
        score = sum(1 for sub in submissions_to_create if sub.is_correct)
        
        attempt.score = score
        attempt.is_completed = True
        attempt.end_time = timezone.now()
        attempt.save()

        # Track activities and progress
        user, guest_user = get_user_or_guest(request)
        duration_minutes = None
        if attempt.start_time and attempt.end_time:
            duration = attempt.end_time - attempt.start_time
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Track quiz completion
        track_quiz_completed(user, guest_user, attempt, duration_minutes)
        
        # Track individual question answers
        for submission in submissions_to_create:
            question = Question.objects.get(id=submission.question_id)
            track_question_answered(user, guest_user, question, submission.is_correct)

        # Update guest user stats if applicable
        if guest_user:
            guest_user.total_quizzes_completed += 1
            guest_user.total_questions_answered += len(submissions_to_create)
            guest_user.save()

        serializer = QuizAttemptResultSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='end')
    def end_exam(self, request, pk=None):
        user_filter = get_user_queryset_filter(request)
        
        try:
            attempt = QuizAttempt.objects.get(
                Q(pk=pk) & user_filter & Q(is_completed=False)
            )
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Active quiz attempt not found."}, status=status.HTTP_404_NOT_FOUND)

        correct_answers = UserSubmission.objects.filter(attempt=attempt, is_correct=True).count()
        
        attempt.score = correct_answers
        attempt.is_completed = True
        attempt.end_time = timezone.now()
        attempt.save()

        # Track quiz completion
        user, guest_user = get_user_or_guest(request)
        duration_minutes = None
        if attempt.start_time and attempt.end_time:
            duration = attempt.end_time - attempt.start_time
            duration_minutes = int(duration.total_seconds() / 60)
        
        track_quiz_completed(user, guest_user, attempt, duration_minutes)

        # Update guest user stats if applicable
        if guest_user:
            guest_user.total_quizzes_completed += 1
            guest_user.save()

        serializer = QuizAttemptResultSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ===================================================================
# VIEWSETS FOR DAILY TARGETS AND PROGRESS TRACKING
# ===================================================================

class DailyTargetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user daily targets - works for both users and guests"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = UniversalDailyTargetSerializer
    
    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        return DailyTarget.objects.filter(user_filter)
    
    def perform_create(self, serializer):
        user, guest_user = get_user_or_guest(self.request)
        if user:
            serializer.save(user=user)
        else:
            serializer.save(guest_user=guest_user)
    
    @action(detail=False, methods=['post'])
    def set_targets(self, request):
        """Bulk set multiple targets at once"""
        targets_data = request.data.get('targets', [])
        
        if not isinstance(targets_data, list):
            return Response(
                {"error": "Targets must be a list"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user, guest_user = get_user_or_guest(request)
        created_targets = []
        updated_targets = []
        
        for target_data in targets_data:
            target_type = target_data.get('target_type')
            target_value = target_data.get('target_value')
            
            if not target_type or not target_value:
                continue
            
            if user:
                target, created = DailyTarget.objects.update_or_create(
                    user=user,
                    target_type=target_type,
                    defaults={
                        'target_value': target_value,
                        'is_active': target_data.get('is_active', True)
                    }
                )
            else:
                target, created = DailyTarget.objects.update_or_create(
                    guest_user=guest_user,
                    target_type=target_type,
                    defaults={
                        'target_value': target_value,
                        'is_active': target_data.get('is_active', True)
                    }
                )
            
            if created:
                created_targets.append(target)
            else:
                updated_targets.append(target)
        
        return Response({
            "created": len(created_targets),
            "updated": len(updated_targets),
            "targets": UniversalDailyTargetSerializer(created_targets + updated_targets, many=True).data
        })

    @action(detail=False, methods=['get'])
    def active_targets(self, request):
        """Get only active targets"""
        targets = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(targets, many=True)
        return Response(serializer.data)

class DailyProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing daily progress - works for both users and guests"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = UniversalDailyProgressSerializer
    
    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        queryset = DailyProgress.objects.filter(user_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # Filter by target type
        target_type = self.request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's progress for all target types"""
        today = date.today()
        user_filter = get_user_queryset_filter(request)
        progress = DailyProgress.objects.filter(user_filter, date=today)
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def week(self, request):
        """Get this week's progress"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        user_filter = get_user_queryset_filter(request)
        progress = DailyProgress.objects.filter(
            user_filter,
            date__range=[week_start, week_end]
        ).order_by('date')
        
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def month(self, request):
        """Get this month's progress"""
        today = date.today()
        month_start = today.replace(day=1)
        
        user_filter = get_user_queryset_filter(request)
        progress = DailyProgress.objects.filter(
            user_filter,
            date__gte=month_start,
            date__lte=today
        ).order_by('date')
        
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)

class WeeklyProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing weekly progress summaries"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = WeeklyProgressSerializer
    
    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        return WeeklyProgress.objects.filter(user_filter).order_by('-week_start_date')

    @action(detail=False, methods=['get'])
    def current_week(self, request):
        """Get current week's progress"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        user_filter = get_user_queryset_filter(request)
        progress = WeeklyProgress.objects.filter(
            user_filter,
            week_start_date=week_start
        )
        
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)

class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user activities"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = UniversalUserActivitySerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        queryset = UserActivity.objects.filter(user_filter).select_related(
            'question', 'quiz_attempt__quiz'
        )
        
        # Filter by activity type
        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(activity_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(activity_date__lte=end_date)
        
        return queryset.order_by('-activity_time')
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's activities"""
        today = date.today()
        activities = self.get_queryset().filter(activity_date=today)
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get activity summary statistics"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        user_filter = get_user_queryset_filter(request)
        user_activities = UserActivity.objects.filter(user_filter)
        
        summary = {
            'today': {
                'questions_answered': user_activities.filter(
                    activity_date=today,
                    activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
                ).count(),
                'quizzes_completed': user_activities.filter(
                    activity_date=today,
                    activity_type__in=[
                        UserActivity.ActivityType.QUIZ_COMPLETED,
                        UserActivity.ActivityType.MODEL_TEST_COMPLETED
                    ]
                ).count(),
            },
            'this_week': {
                'questions_answered': user_activities.filter(
                    activity_date__gte=week_start,
                    activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
                ).count(),
                'quizzes_completed': user_activities.filter(
                    activity_date__gte=week_start,
                    activity_type__in=[
                        UserActivity.ActivityType.QUIZ_COMPLETED,
                        UserActivity.ActivityType.MODEL_TEST_COMPLETED
                    ]
                ).count(),
            },
            'this_month': {
                'questions_answered': user_activities.filter(
                    activity_date__gte=month_start,
                    activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
                ).count(),
                'quizzes_completed': user_activities.filter(
                    activity_date__gte=month_start,
                    activity_type__in=[
                        UserActivity.ActivityType.QUIZ_COMPLETED,
                        UserActivity.ActivityType.MODEL_TEST_COMPLETED
                    ]
                ).count(),
            }
        }
        
        return Response(summary)

class StreakViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user streaks"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    serializer_class = UniversalStreakSerializer
    
    def get_queryset(self):
        user_filter = get_user_queryset_filter(self.request)
        return Streak.objects.filter(user_filter)

    @action(detail=False, methods=['get'])
    def detailed(self, request):
        """Get detailed streak information with motivational messages"""
        streaks = self.get_queryset()
        serializer = StreakDetailSerializer(streaks, many=True)
        return Response(serializer.data)

class ProgressDashboardView(APIView):
    """Comprehensive dashboard view for user progress - works for both users and guests"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    
    def get(self, request):
        user, guest_user = get_user_or_guest(request)
        user_filter = get_user_queryset_filter(request)
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Get today's progress
        today_progress = DailyProgress.objects.filter(user_filter, date=today)
        
        # Get this week's progress summary
        weekly_progress = WeeklyProgress.objects.filter(
            user_filter, 
            week_start_date=week_start
        )
        
        # Get user streaks
        streaks = Streak.objects.filter(user_filter)
        
        # Get recent activities (last 10)
        recent_activities = UserActivity.objects.filter(user_filter).select_related(
            'question', 'quiz_attempt__quiz'
        ).order_by('-activity_time')[:10]
        
        # Get user targets
        targets = DailyTarget.objects.filter(user_filter, is_active=True)
        
        # Calculate summary statistics
        today_activities = UserActivity.objects.filter(user_filter, activity_date=today)
        
        total_questions_today = today_activities.filter(
            activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
        ).count()
        
        total_quizzes_today = today_activities.filter(
            activity_type__in=[
                UserActivity.ActivityType.QUIZ_COMPLETED,
                UserActivity.ActivityType.MODEL_TEST_COMPLETED
            ]
        ).count()
        
        total_study_time_today = today_activities.aggregate(
            total_time=Sum('duration_minutes')
        )['total_time'] or 0
        
        # Weekly statistics
        week_activities = UserActivity.objects.filter(
            user_filter, 
            activity_date__range=[week_start, week_end]
        )
        
        weekly_questions = week_activities.filter(
            activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
        ).count()
        
        weekly_quizzes = week_activities.filter(
            activity_type__in=[
                UserActivity.ActivityType.QUIZ_COMPLETED,
                UserActivity.ActivityType.MODEL_TEST_COMPLETED
            ]
        ).count()
        
        weekly_study_time = week_activities.aggregate(
            total_time=Sum('duration_minutes')
        )['total_time'] or 0
        
        # Determine user type and identifier
        user_type = 'guest' if guest_user else 'registered'
        user_identifier = str(guest_user.guest_id) if guest_user else user.username
        
        dashboard_data = {
            'today_progress': UniversalDailyProgressSerializer(today_progress, many=True).data,
            'weekly_progress': WeeklyProgressSerializer(weekly_progress, many=True).data,
            'streaks': UniversalStreakSerializer(streaks, many=True).data,
            'recent_activities': UniversalUserActivitySerializer(recent_activities, many=True).data,
            'targets': UniversalDailyTargetSerializer(targets, many=True).data,
            'total_questions_solved_today': total_questions_today,
            'total_quizzes_completed_today': total_quizzes_today,
            'total_study_time_today': total_study_time_today,
            'weekly_questions_solved': weekly_questions,
            'weekly_quizzes_completed': weekly_quizzes,
            'weekly_study_time': weekly_study_time,
            'user_type': user_type,
            'user_identifier': user_identifier,
        }
        
        return Response(dashboard_data)

class ProgressAnalyticsView(APIView):
    """Advanced analytics view for progress tracking"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    
    def get(self, request):
        user_filter = get_user_queryset_filter(request)
        days = int(request.query_params.get('days', 30))  # Default 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get daily progress for the period
        daily_progress = DailyProgress.objects.filter(
            user_filter,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Group by target type
        progress_by_type = defaultdict(list)
        for progress in daily_progress:
            progress_by_type[progress.target_type].append({
                'date': progress.date,
                'current_value': progress.current_value,
                'target_value': progress.target_value,
                'completion_percentage': progress.completion_percentage,
                'is_completed': progress.is_completed
            })
        
        # Calculate streaks and completion rates
        analytics = {}
        for target_type, progress_list in progress_by_type.items():
            completed_days = len([p for p in progress_list if p['is_completed']])
            total_days = len(progress_list)
            completion_rate = (completed_days / total_days * 100) if total_days > 0 else 0
            
            # Calculate average completion percentage
            avg_completion = sum(p['completion_percentage'] for p in progress_list) / len(progress_list) if progress_list else 0
            
            analytics[target_type] = {
                'progress_data': progress_list,
                'completion_rate': round(completion_rate, 2),
                'completed_days': completed_days,
                'total_days': total_days,
                'average_completion': round(avg_completion, 2),
                'target_type_display': dict(DailyTarget.TargetType.choices)[target_type]
            }
        
        return Response({
            'period': f'{days} days',
            'start_date': start_date,
            'end_date': end_date,
            'analytics': analytics
        })

# ===================================================================
# GUEST USER SPECIFIC VIEWS
# ===================================================================

class GuestUserStatsView(APIView):
    """Get guest user statistics"""
    authentication_classes = [FlexibleAuthentication]
    permission_classes = [IsAuthenticatedOrGuest]
    
    def get(self, request):
        if not getattr(request.user, 'is_guest', False):
            return Response(
                {"error": "This endpoint is only for guest users"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest_user = request.user.guest_user
        
        # Get basic stats
        stats = {
            'guest_id': guest_user.guest_id,
            'total_questions_answered': guest_user.total_questions_answered,
            'total_quizzes_completed': guest_user.total_quizzes_completed,
            'account_age_days': (timezone.now().date() - guest_user.created_at.date()).days,
            'last_active': guest_user.last_active,
        }
        
        # Get recent activity counts
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        recent_stats = {
            'questions_today': UserActivity.objects.filter(
                guest_user=guest_user,
                activity_date=today,
                activity_type=UserActivity.ActivityType.QUESTION_ANSWERED
            ).count(),
            'quizzes_this_week': UserActivity.objects.filter(
                guest_user=guest_user,
                activity_date__gte=week_start,
                activity_type__in=[
                    UserActivity.ActivityType.QUIZ_COMPLETED,
                    UserActivity.ActivityType.MODEL_TEST_COMPLETED
                ]
            ).count(),
        }
        
        return Response({
            'guest_stats': stats,
            'recent_activity': recent_stats
        })

# ===================================================================
# UTILITY FUNCTIONS FOR PROGRESS TRACKING (UPDATED FOR GUEST SUPPORT)
# ===================================================================

def track_question_answered(user, guest_user, question, is_correct=False, duration_minutes=None):
    """Track when a user or guest answers a question"""
    if user:
        activity = UserActivity.objects.create(
            user=user,
            activity_type=UserActivity.ActivityType.QUESTION_ANSWERED,
            question=question,
            duration_minutes=duration_minutes,
            points_earned=1 if is_correct else 0
        )
    else:
        activity = UserActivity.objects.create(
            guest_user=guest_user,
            activity_type=UserActivity.ActivityType.QUESTION_ANSWERED,
            question=question,
            duration_minutes=duration_minutes,
            points_earned=1 if is_correct else 0
        )
    
    # Update daily progress for questions solved
    update_daily_progress(user, guest_user, DailyTarget.TargetType.QUESTIONS_SOLVED, 1)
    
    # Update streak
    update_streak(user, guest_user, DailyTarget.TargetType.QUESTIONS_SOLVED)
    
    return activity

def track_quiz_completed(user, guest_user, quiz_attempt, duration_minutes=None):
    """Track when a user or guest completes a quiz"""
    activity_type = (
        UserActivity.ActivityType.MODEL_TEST_COMPLETED 
        if quiz_attempt.quiz.quiz_type == Quiz.QuizType.MODEL_TEST 
        else UserActivity.ActivityType.QUIZ_COMPLETED
    )
    
    if user:
        activity = UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            quiz_attempt=quiz_attempt,
            duration_minutes=duration_minutes,
            points_earned=quiz_attempt.score
        )
    else:
        activity = UserActivity.objects.create(
            guest_user=guest_user,
            activity_type=activity_type,
            quiz_attempt=quiz_attempt,
            duration_minutes=duration_minutes,
            points_earned=quiz_attempt.score
        )
    
    # Update daily progress
    if quiz_attempt.quiz.quiz_type == Quiz.QuizType.MODEL_TEST:
        update_daily_progress(user, guest_user, DailyTarget.TargetType.MODEL_TESTS_TAKEN, 1)
        update_streak(user, guest_user, DailyTarget.TargetType.MODEL_TESTS_TAKEN)
    else:
        update_daily_progress(user, guest_user, DailyTarget.TargetType.QUIZ_ATTEMPTS, 1)
        update_streak(user, guest_user, DailyTarget.TargetType.QUIZ_ATTEMPTS)
    
    return activity

def update_daily_progress(user, guest_user, target_type, increment_value=1, activity_date=None):
    """Update daily progress for a specific target type"""
    if activity_date is None:
        activity_date = date.today()
    
    # Get user's target for this type
    try:
        if user:
            target = DailyTarget.objects.get(user=user, target_type=target_type, is_active=True)
        else:
            target = DailyTarget.objects.get(guest_user=guest_user, target_type=target_type, is_active=True)
        target_value = target.target_value
    except DailyTarget.DoesNotExist:
        target_value = 0  # No target set
    
    # Get or create daily progress
    if user:
        progress, created = DailyProgress.objects.get_or_create(
            user=user,
            target_type=target_type,
            date=activity_date,
            defaults={
                'target_value': target_value,
                'current_value': 0
            }
        )
    else:
        progress, created = DailyProgress.objects.get_or_create(
            guest_user=guest_user,
            target_type=target_type,
            date=activity_date,
            defaults={
                'target_value': target_value,
                'current_value': 0
            }
        )
    
    # Update current value
    progress.current_value += increment_value
    progress.target_value = target_value  # Update in case target changed
    progress.save()  # This will auto-calculate completion percentage
    
    # Update weekly progress
    update_weekly_progress(user, guest_user, target_type, activity_date)
    
    return progress

def update_weekly_progress(user, guest_user, target_type, activity_date=None):
    """Update weekly progress summary"""
    if activity_date is None:
        activity_date = date.today()
    
    # Calculate week start (Monday)
    week_start = activity_date - timedelta(days=activity_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get daily progress for this week
    if user:
        daily_progress = DailyProgress.objects.filter(
            user=user,
            target_type=target_type,
            date__range=[week_start, week_end]
        )
    else:
        daily_progress = DailyProgress.objects.filter(
            guest_user=guest_user,
            target_type=target_type,
            date__range=[week_start, week_end]
        )
    
    total_target = daily_progress.aggregate(Sum('target_value'))['target_value__sum'] or 0
    total_achieved = daily_progress.aggregate(Sum('current_value'))['current_value__sum'] or 0
    days_completed = daily_progress.filter(is_completed=True).count()
    
    completion_percentage = (total_achieved / total_target * 100) if total_target > 0 else 0
    
    # Update or create weekly progress
    if user:
        weekly_progress, created = WeeklyProgress.objects.update_or_create(
            user=user,
            target_type=target_type,
            week_start_date=week_start,
            defaults={
                'total_target': total_target,
                'total_achieved': total_achieved,
                'days_completed': days_completed,
                'completion_percentage': completion_percentage
            }
        )
    else:
        weekly_progress, created = WeeklyProgress.objects.update_or_create(
            guest_user=guest_user,
            target_type=target_type,
            week_start_date=week_start,
            defaults={
                'total_target': total_target,
                'total_achieved': total_achieved,
                'days_completed': days_completed,
                'completion_percentage': completion_percentage
            }
        )
    
    return weekly_progress

def update_streak(user, guest_user, target_type, activity_date=None):
    """Update user or guest streak for a target type"""
    if activity_date is None:
        activity_date = date.today()
    
    if user:
        streak, created = Streak.objects.get_or_create(
            user=user,
            target_type=target_type
        )
    else:
        streak, created = Streak.objects.get_or_create(
            guest_user=guest_user,
            target_type=target_type
        )
    
    streak.update_streak(activity_date)
    return streak
