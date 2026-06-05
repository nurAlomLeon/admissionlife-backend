# Progress Tracker App

This Django app handles daily targets and progress tracking functionality for the QBank project.

## Features

### Models
- **DailyTarget**: Store user's daily targets (questions solved, tests taken, practice time, etc.)
- **DailyProgress**: Track daily progress for each target type
- **WeeklyProgress**: Weekly progress summaries
- **UserActivity**: Log user activities for progress tracking
- **Streak**: Track user streaks for different activities

### API Endpoints
All endpoints are available under `/api/progress/`:

- `GET/POST /api/progress/daily-targets/` - Manage daily targets
- `GET/POST /api/progress/daily-progress/` - Manage daily progress
- `GET /api/progress/daily-progress/today/` - Get today's progress
- `GET /api/progress/weekly-progress/` - View weekly progress
- `GET/POST /api/progress/user-activities/` - Manage user activities
- `GET /api/progress/streaks/` - View user streaks

### Target Types
- `QUESTIONS_SOLVED` - Questions Solved
- `MODEL_TESTS_TAKEN` - Model Tests Taken
- `PRACTICE_TIME_MINUTES` - Practice Time (Minutes)
- `QUIZ_ATTEMPTS` - Quiz Attempts

### Activity Types
- `QUESTION_ANSWERED` - Question Answered
- `QUIZ_COMPLETED` - Quiz Completed
- `MODEL_TEST_COMPLETED` - Model Test Completed
- `PRACTICE_SESSION` - Practice Session

## Usage

### Setting a Daily Target
```python
# Create a daily target for solving 50 questions
target = DailyTarget.objects.create(
    user=user,
    target_type=DailyTarget.TargetType.QUESTIONS_SOLVED,
    target_value=50
)
```

### Updating Progress
```python
# Update daily progress
progress, created = DailyProgress.objects.get_or_create(
    user=user,
    target_type=DailyTarget.TargetType.QUESTIONS_SOLVED,
    date=date.today(),
    defaults={'target_value': 50}
)
progress.current_value += 1
progress.save()  # Auto-calculates completion percentage
```

### Tracking Streaks
```python
# Update streak when user completes a target
streak, created = Streak.objects.get_or_create(
    user=user,
    target_type=DailyTarget.TargetType.QUESTIONS_SOLVED
)
streak.update_streak()  # Automatically manages streak logic
```

## Migration Notes

This app contains models that were previously in the `api` app. The constraint names have been prefixed with `progress_` to avoid conflicts.

## Authentication

The app uses `FlexibleAuthentication` from the api app to support both regular users and guest users.
