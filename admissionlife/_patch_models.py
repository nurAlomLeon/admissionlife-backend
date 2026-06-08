import os

mfile = os.path.join(os.path.dirname(__file__), 'models.py')

with open(mfile, 'r', encoding='utf-8') as f:
    content = f.read()

if 'UserProfile' in content:
    print('ALREADY_PATCHED')
else:
    lines = content.split('\n')
    lines.insert(2, 'from django.db.models.signals import post_save')
    lines.insert(3, 'from django.dispatch import receiver')

    block = '''
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    hsc_year = models.PositiveIntegerField(null=True, blank=True)
    mobile_number = models.CharField(max_length=11, blank=True, default='')
    college_name = models.CharField(max_length=200, blank=True, default='')
    address = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'admissionlife'

    def __str__(self):
        return f'Profile for {self.user.username}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
'''
    with open(mfile, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + block)
    print('PATCHED')
