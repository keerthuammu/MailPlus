import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mailpulse.settings')
django.setup()

from tracker.models import Email, EmailOpen
output = []
for e in Email.objects.all():
    output.append(f"Email to {e.recipient}: open_count={e.open_count}, is_opened={e.is_opened}")
    for o in e.opens.all():
        output.append(f"  - Open at {o.opened_at} from IP {o.ip_address}")

with open('db_out.txt', 'w') as f:
    f.write('\n'.join(output))
