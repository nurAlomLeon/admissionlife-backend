# Migration to safely remove progress tracking models from api app

from django.db import migrations


def drop_progress_constraints(apps, schema_editor):
    """
    Manually drop constraints that might be preventing model removal
    """
    db_alias = schema_editor.connection.alias
    
    # List of constraint names that might exist and need to be dropped
    constraint_names = [
        'daily_target_must_have_user_or_guest',
        'daily_target_cannot_have_both_user_and_guest', 
        'unique_user_target_type',
        'unique_guest_target_type',
        'daily_progress_must_have_user_or_guest',
        'daily_progress_cannot_have_both_user_and_guest',
        'unique_user_target_date', 
        'unique_guest_target_date',
        'weekly_progress_must_have_user_or_guest',
        'weekly_progress_cannot_have_both_user_and_guest',
        'unique_user_week_target',
        'unique_guest_week_target',
        'user_activity_must_have_user_or_guest',
        'user_activity_cannot_have_both_user_and_guest',
        'streak_must_have_user_or_guest',
        'streak_cannot_have_both_user_and_guest',
        'unique_user_streak_type',
        'unique_guest_streak_type',
    ]
    
    # Table names that might have these constraints
    table_names = [
        'api_dailytarget',
        'api_dailyprogress', 
        'api_weeklyprogress',
        'api_useractivity',
        'api_streak',
    ]
    
    with schema_editor.connection.cursor() as cursor:
        for table_name in table_names:
            for constraint_name in constraint_names:
                try:
                    # Try to drop the constraint if it exists
                    cursor.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
                    print(f"Dropped constraint {constraint_name} from {table_name}")
                except Exception as e:
                    # Constraint doesn't exist or already dropped, which is fine
                    pass
                    
                try:
                    # Also try with api_ prefix
                    prefixed_name = f"api_{constraint_name}"
                    cursor.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {prefixed_name}")
                    print(f"Dropped constraint {prefixed_name} from {table_name}")
                except Exception as e:
                    # Constraint doesn't exist or already dropped, which is fine
                    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_category_options_category_level_category_order_and_more'),
    ]

    operations = [
        # No-op: The progress models were never created in the api migration chain.
        # They were managed by the progress_tracker app directly.
        migrations.RunPython(
            migrations.RunPython.noop,
            migrations.RunPython.noop,
        ),
    ]
