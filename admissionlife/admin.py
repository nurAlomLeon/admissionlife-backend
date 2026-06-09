import csv
import io

from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.forms.models import BaseInlineFormSet
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone

from .models import (
    Batch, Payment, Enrollment, Exam, ExamQuestion, ExamAttempt, ExamSubmission,
    BatchCategory, Category, Label, Question, Answer, Quiz, QuizAttempt, SavedQuestion, QuestionReport,
    UniversityAnswer, UniversityCategory, UniversityQuestion, UserProfile,
)
from .forms import CsvImportForm, UniversityCsvImportForm
from .services import EnrollmentService


# =============================================================================
# Question Bank Admin (admissionlife-specific models)
# =============================================================================

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    max_num = 6


class UniversityAnswerInline(admin.TabularInline):
    model = UniversityAnswer
    extra = 4
    max_num = 6


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_full_path', 'level', 'parent', 'order', 'get_question_count']
    list_filter = ['level']
    search_fields = ['name']
    ordering = ['level', 'order', 'name']
    list_editable = ['order']
    readonly_fields = ['level']

    fieldsets = (
        (None, {'fields': ('name', 'parent', 'order')}),
        ('Info', {
            'fields': ('level',),
            'classes': ('collapse',),
            'description': 'Level is auto-calculated. 0=Subject, 1=Part, 2=Topic',
        }),
    )

    def get_full_path(self, obj):
        return obj.get_full_path()
    get_full_path.short_description = 'Full Path'

    def get_question_count(self, obj):
        if obj.is_leaf():
            return Question.objects.filter(category=obj).count()
        descendant_ids = [d.id for d in obj.get_descendants() if d.is_leaf()]
        return Question.objects.filter(category_id__in=descendant_ids).count()
    get_question_count.short_description = 'Questions'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(UniversityCategory)
class UniversityCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_full_path', 'level', 'parent', 'order', 'get_question_count']
    list_filter = ['level']
    search_fields = ['name']
    ordering = ['level', 'order', 'name']
    list_editable = ['order']
    readonly_fields = ['level']

    def get_full_path(self, obj):
        return obj.get_full_path()

    get_full_path.short_description = 'Full Path'

    def get_question_count(self, obj):
        if obj.is_leaf():
            return UniversityQuestion.objects.filter(category=obj).count()
        descendant_ids = [d.id for d in obj.get_descendants() if d.is_leaf()]
        return UniversityQuestion.objects.filter(category_id__in=descendant_ids).count()

    get_question_count.short_description = 'Questions'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ['question_text_short', 'get_category_path', 'get_labels', 'created_at']
    list_filter = ['category', 'labels', 'created_at']
    search_fields = ['question_text', 'category__name']
    filter_horizontal = ['labels']
    change_list_template = "admin/admissionlife/question/change_list.html"

    def question_text_short(self, obj):
        text = obj.question_text
        return text[:80] + '...' if len(text) > 80 else text
    question_text_short.short_description = 'Question'

    def get_category_path(self, obj):
        return obj.category.get_full_path() if obj.category else '—'
    get_category_path.short_description = 'Category'

    def get_labels(self, obj):
        return ', '.join(obj.labels.values_list('name', flat=True)) or '—'
    get_labels.short_description = 'Labels'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('labels').select_related('category')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='admissionlife_question_import_csv'),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]
                selected_category = form.cleaned_data.get('category')

                try:
                    with transaction.atomic():
                        decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                        reader = csv.DictReader(decoded_file)

                        required_columns = {'Item Type', 'Question Title', 'Answer Text', 'Answer Correct/InCorrect'}
                        if not required_columns.issubset(reader.fieldnames or set()):
                            missing = required_columns - set(reader.fieldnames or [])
                            self.message_user(request, f"Missing required columns: {', '.join(missing)}", messages.ERROR)
                            return redirect("..")

                        questions_created = 0
                        answers_created = 0
                        current_question = None

                        for row in reader:
                            item_type = row.get('Item Type', '').strip().lower()

                            if item_type == 'question':
                                question_text = row.get('Question Title', '').strip()
                                if not question_text:
                                    continue

                                labels_str = row.get('Hints', '').strip()

                                if selected_category:
                                    category = selected_category
                                else:
                                    category_name = row.get('Categories', '').strip()
                                    category = None
                                    if category_name:
                                        category, _ = Category.objects.get_or_create(
                                            name=category_name,
                                            defaults={'level': 2}
                                        )

                                current_question = Question.objects.create(
                                    question_text=question_text,
                                    explanation=row.get('Question Answer Info', '').strip(),
                                    category=category
                                )
                                questions_created += 1

                                if labels_str:
                                    label_names = [name.strip() for name in labels_str.split(',') if name.strip()]
                                    for name in label_names:
                                        label, _ = Label.objects.get_or_create(name=name)
                                        current_question.labels.add(label)

                            elif item_type == 'answer' and current_question:
                                answer_text = row.get('Answer Text', '').strip()
                                if not answer_text:
                                    continue

                                is_correct = str(row.get('Answer Correct/InCorrect', '')).strip() == '1'
                                Answer.objects.create(
                                    question=current_question,
                                    text=answer_text,
                                    is_correct=is_correct
                                )
                                answers_created += 1

                    category_msg = f" into category '{selected_category.get_full_path()}'" if selected_category else ""
                    self.message_user(
                        request,
                        f"Successfully imported {questions_created} questions and {answers_created} answers{category_msg}.",
                        messages.SUCCESS
                    )
                    return redirect("..")

                except Exception as e:
                    self.message_user(request, f"An error occurred during import: {str(e)}", messages.ERROR)
        else:
            form = CsvImportForm()

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['title'] = "Import Questions from CSV"

        return render(request, "admin/admissionlife/question/csv_form.html", context)


@admin.register(UniversityQuestion)
class UniversityQuestionAdmin(admin.ModelAdmin):
    inlines = [UniversityAnswerInline]
    list_display = ['question_text_short', 'get_category_path', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['question_text', 'category__name']

    def question_text_short(self, obj):
        text = obj.question_text
        return text[:80] + '...' if len(text) > 80 else text

    question_text_short.short_description = 'Question'

    def get_category_path(self, obj):
        return obj.category.get_full_path() if obj.category else '—'

    get_category_path.short_description = 'Category'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv),
                name='admissionlife_universityquestion_import_csv',
            ),
        ]
        return custom_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = UniversityCsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]
                selected_category = form.cleaned_data.get('category')

                try:
                    with transaction.atomic():
                        decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                        reader = csv.DictReader(decoded_file)

                        required_columns = {'Item Type', 'Question Title', 'Answer Text', 'Answer Correct/InCorrect'}
                        if not required_columns.issubset(reader.fieldnames or set()):
                            missing = required_columns - set(reader.fieldnames or [])
                            self.message_user(
                                request,
                                f"Missing required columns: {', '.join(missing)}",
                                messages.ERROR,
                            )
                            return redirect("..")

                        questions_created = 0
                        answers_created = 0
                        current_question = None

                        for row in reader:
                            item_type = row.get('Item Type', '').strip().lower()

                            if item_type == 'question':
                                question_text = row.get('Question Title', '').strip()
                                if not question_text:
                                    continue

                                if selected_category:
                                    category = selected_category
                                else:
                                    category_path = row.get('Categories', '').strip()
                                    category = self._get_or_create_university_category_from_path(category_path)

                                current_question = UniversityQuestion.objects.create(
                                    question_text=question_text,
                                    explanation=row.get('Question Answer Info', '').strip(),
                                    category=category,
                                )
                                questions_created += 1

                            elif item_type == 'answer' and current_question:
                                answer_text = row.get('Answer Text', '').strip()
                                if not answer_text:
                                    continue

                                is_correct = str(
                                    row.get('Answer Correct/InCorrect', '')
                                ).strip() == '1'
                                UniversityAnswer.objects.create(
                                    question=current_question,
                                    text=answer_text,
                                    is_correct=is_correct,
                                )
                                answers_created += 1

                    category_msg = (
                        f" into category '{selected_category.get_full_path()}'"
                        if selected_category else ""
                    )
                    self.message_user(
                        request,
                        f"Successfully imported {questions_created} university questions and {answers_created} answers{category_msg}.",
                        messages.SUCCESS,
                    )
                    return redirect("..")

                except Exception as e:
                    self.message_user(
                        request,
                        f"An error occurred during import: {str(e)}",
                        messages.ERROR,
                    )
        else:
            form = UniversityCsvImportForm()

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['title'] = "Import University Questions from CSV"

        return render(request, "admin/admissionlife/question/csv_form.html", context)

    def _get_or_create_university_category_from_path(self, category_path):
        if not category_path:
            return None

        parts = [
            part.strip()
            for part in category_path.replace('→', '>').split('>')
            if part.strip()
        ]
        parent = None

        for part in parts:
            category, _ = UniversityCategory.objects.get_or_create(
                name=part,
                parent=parent,
            )
            parent = category

        return parent


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'question_short', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['text', 'question__question_text']

    def text_short(self, obj):
        return obj.text[:60] + '...' if len(obj.text) > 60 else obj.text
    text_short.short_description = 'Answer Text'

    def question_short(self, obj):
        return str(obj.question)
    question_short.short_description = 'Question'


@admin.register(QuestionReport)
class QuestionReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_short', 'status', 'reported_at']
    list_filter = ['status', 'reported_at']
    search_fields = ['user__username', 'question__question_text', 'reason']
    list_editable = ['status']

    def question_short(self, obj):
        return str(obj.question.question_text)[:50] + '...'
    question_short.short_description = 'Question'


@admin.register(SavedQuestion)
class SavedQuestionAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_short', 'saved_at']
    search_fields = ['user__username', 'question__question_text']

    def question_short(self, obj):
        return str(obj.question.question_text)[:50] + '...'
    question_short.short_description = 'Question'


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 0


class BatchExamInlineForm(forms.ModelForm):
    def validate_unique(self):
        # Inline-level validation handles final sequence uniqueness, allowing swaps.
        pass


class BatchExamInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_orders = set()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            order = form.cleaned_data.get('order')
            if order is None:
                continue
            if order < 1:
                raise ValidationError('Exam sequence must be a positive number.')
            if order in seen_orders:
                raise ValidationError('Each exam in this batch must have a unique sequence number.')
            seen_orders.add(order)


class BatchExamInline(admin.TabularInline):
    model = Exam
    form = BatchExamInlineForm
    formset = BatchExamInlineFormSet
    fields = ('title', 'duration_minutes', 'order', 'passing_score', 'unlock_datetime', 'is_active')
    extra = 1
    ordering = ('order',)
    verbose_name = 'Exam'
    verbose_name_plural = 'Exams'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'order':
            formfield.label = 'Sequence'
            formfield.help_text = 'Controls recorded batch progression and exam display order.'
        elif db_field.name == 'unlock_datetime':
            formfield.label = 'Start date/time'
            formfield.help_text = 'Used for live batches. Leave blank for recorded batches.'
        return formfield


@admin.register(BatchCategory)
class BatchCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    search_fields = ('name',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch_type', 'price', 'is_active', 'created_at')
    list_filter = ('batch_type', 'is_active', 'categories')
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)
    fields = ('name', 'description', 'banner_image', 'batch_type', 'categories', 'price', 'is_active')
    inlines = [BatchExamInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is not Exam:
            return super().save_formset(request, form, formset, change)

        with transaction.atomic():
            instances = formset.save(commit=False)

            for deleted_obj in formset.deleted_objects:
                deleted_obj.delete()

            existing_instances = [instance for instance in instances if instance.pk]
            new_instances = [instance for instance in instances if not instance.pk]

            if existing_instances:
                max_order = Exam.objects.filter(batch=form.instance).aggregate(Max('order'))['order__max'] or 0
                temporary_order = max_order + 1000

                for index, instance in enumerate(existing_instances, start=1):
                    Exam.objects.filter(pk=instance.pk).update(order=temporary_order + index)

            for instance in existing_instances + new_instances:
                instance.batch = form.instance
                instance.save()

            formset.save_m2m()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'batch', 'payment_method', 'transaction_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('transaction_id', 'sender_number', 'user__username')

    def save_model(self, request, obj, form, change):
        status_changed = 'status' in form.changed_data
        if obj.status != Payment.PaymentStatus.PENDING and obj.reviewed_at is None:
            obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)

        if obj.status == Payment.PaymentStatus.APPROVED:
            EnrollmentService.create_enrollment(
                user=obj.user,
                batch=obj.batch,
                payment=obj,
            )
            return

        if status_changed:
            Enrollment.objects.filter(user=obj.user, batch=obj.batch).delete()


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'batch', 'enrolled_at')
    search_fields = ('user__username', 'batch__name')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'order', 'duration_minutes', 'unlock_datetime', 'is_active')
    list_filter = ('batch', 'is_active')
    search_fields = ('title',)
    inlines = [ExamQuestionInline]
    change_list_template = "admin/admissionlife/exam/change_list.html"
    change_form_template = "admin/admissionlife/exam/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name='admissionlife_exam_import_csv',
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            exam_id = request.POST.get("exam_id")

            if not csv_file:
                self.message_user(request, "No file was uploaded.", messages.ERROR)
                return redirect("..")

            if not exam_id:
                self.message_user(request, "Please select an exam.", messages.ERROR)
                return redirect("..")

            try:
                exam = Exam.objects.get(pk=exam_id)
            except Exam.DoesNotExist:
                self.message_user(request, "Exam not found.", messages.ERROR)
                return redirect("..")

            try:
                decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.reader(decoded_file)

                # Skip header row
                try:
                    next(reader)
                except StopIteration:
                    self.message_user(request, "CSV file is empty.", messages.ERROR)
                    return redirect("..")

                questions_to_create = []
                errors = []
                row_num = 1  # 1-indexed after header

                for row in reader:
                    row_num += 1
                    # Expected columns: Question Title, Answer 1, Answer 2, Answer 3, Answer 4, Correct Answer, Explanation
                    if len(row) < 6:
                        errors.append(f"Row {row_num}: fewer than 6 columns")
                        continue

                    question_text = row[0].strip()
                    if not question_text:
                        errors.append(f"Row {row_num}: missing question text")
                        continue

                    answers = [row[i].strip() for i in range(1, 5)]
                    if any(len(a) > 255 for a in answers):
                        errors.append(f"Row {row_num}: answer exceeds 255 characters")
                        continue

                    try:
                        correct_answer = int(row[5].strip())
                        if correct_answer < 1 or correct_answer > 4:
                            raise ValueError
                    except (ValueError, IndexError):
                        errors.append(f"Row {row_num}: correct answer must be 1-4")
                        continue

                    explanation = row[6].strip() if len(row) > 6 else ''

                    questions_to_create.append(ExamQuestion(
                        exam=exam,
                        question_text=question_text,
                        answer_1=answers[0],
                        answer_2=answers[1],
                        answer_3=answers[2],
                        answer_4=answers[3],
                        correct_answer=correct_answer,
                        explanation=explanation,
                    ))

                with transaction.atomic():
                    ExamQuestion.objects.bulk_create(questions_to_create)

                msg = f"Successfully imported {len(questions_to_create)} questions into '{exam.title}'."
                if errors:
                    msg += f" {len(errors)} rows skipped."
                self.message_user(request, msg, messages.SUCCESS)
                return redirect("..")

            except Exception as e:
                self.message_user(request, f"Error during import: {str(e)}", messages.ERROR)
                return redirect("..")

        # GET request - show the form
        exams = Exam.objects.select_related('batch').all()
        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['title'] = "Import Questions from CSV"
        context['exams'] = exams
        context['selected_exam_id'] = request.GET.get('exam_id')
        return render(request, "admin/admissionlife/exam/csv_import_form.html", context)


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'score', 'is_completed', 'start_time')
    list_filter = ('is_completed',)
    readonly_fields = (
        'user', 'exam', 'score', 'total_questions', 'correct_count',
        'incorrect_count', 'unanswered_count', 'start_time', 'end_time', 'is_completed',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
  
  
@admin.register(UserProfile)  
class UserProfileAdmin(admin.ModelAdmin):  
    list_display = ('user', 'hsc_year', 'mobile_number', 'college_name', 'address')  
    search_fields = ('user__username', 'user__email', 'mobile_number', 'college_name')  
    list_filter = ('hsc_year',)  
    raw_id_fields = ('user',) 
