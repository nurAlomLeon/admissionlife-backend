import os

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/admissionlife')

with open('serializers.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """class CustomUserDetailsSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = DjangoUser
        fields = ['pk', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['pk', 'username', 'email']"""

new = """class CustomUserDetailsSerializer(serializers.ModelSerializer):
    hsc_year = serializers.IntegerField(
        source='profile.hsc_year', read_only=True, allow_null=True)
    mobile_number = serializers.CharField(
        source='profile.mobile_number', read_only=True, default='')
    college_name = serializers.CharField(
        source='profile.college_name', read_only=True, default='')
    address = serializers.CharField(
        source='profile.address', read_only=True, default='')

    class Meta:
        model = DjangoUser
        fields = ['pk', 'username', 'email', 'first_name', 'last_name',
                  'hsc_year', 'mobile_number', 'college_name', 'address']
        read_only_fields = ['pk', 'username', 'email']"""

if old in content:
    content = content.replace(old, new)
    with open('serializers.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Flattened CustomUserDetailsSerializer')
else:
    print('OLD TEXT NOT FOUND in serializers.py')
    idx = content.find('CustomUserDetailsSerializer')
    if idx >= 0:
        print(repr(content[idx:idx+350]))
