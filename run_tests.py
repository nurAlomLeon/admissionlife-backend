import subprocess
import sys

result = subprocess.run(
    [sys.executable, "manage.py", "test", "admissionlife", "--verbosity=1"],
    capture_output=True,
    text=True,
    cwd=r"c:\Users\user\Desktop\django\qbank-dj"
)

output = result.stdout + result.stderr
lines = output.split('\n')

# Find the line with "Ran X test(s)" and print from there
for i, line in enumerate(lines):
    if 'Ran ' in line and 'test' in line:
        print('\n'.join(lines[i:]))
        break
else:
    # If not found, check for FAILED or errors
    for i, line in enumerate(lines):
        if 'FAIL' in line or 'ERROR' in line:
            print('\n'.join(lines[max(0,i-2):min(len(lines), i+10)]))
            break
    else:
        print("Could not find summary. Last 5 lines:")
        print('\n'.join(lines[-5:]))

print(f"\nReturn code: {result.returncode}")
