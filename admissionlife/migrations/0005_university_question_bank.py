from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissionlife', '0004_batch_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='UniversityCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('level', models.PositiveIntegerField(default=0)),
                ('order', models.PositiveIntegerField(default=0)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='children', to='admissionlife.universitycategory')),
            ],
            options={
                'verbose_name_plural': 'University Categories',
                'ordering': ['level', 'order', 'name'],
                'unique_together': {('name', 'parent')},
            },
        ),
        migrations.CreateModel(
            name='UniversityQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.TextField(help_text='The main text of the question.')),
                ('question_image', models.ImageField(blank=True, null=True, upload_to='admissionlife/university_questions/')),
                ('explanation', models.TextField(blank=True, null=True)),
                ('explanation_image', models.ImageField(blank=True, null=True, upload_to='admissionlife/university_explanations/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='questions', to='admissionlife.universitycategory')),
            ],
        ),
        migrations.CreateModel(
            name='UniversityAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('image', models.ImageField(blank=True, null=True, upload_to='admissionlife/university_answers/')),
                ('is_correct', models.BooleanField(default=False)),
                ('question', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='answers', to='admissionlife.universityquestion')),
            ],
        ),
    ]
