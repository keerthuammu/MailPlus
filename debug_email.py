import sys
try:
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mailpulse.settings')
    django.setup()
    from tracker.models import Email
    e = Email.objects.latest('sent_at')
    res = f"Recipient: {e.recipient}\nSubject: {e.subject}\nSent at: {e.sent_at}\nOpen count: {e.open_count}\nBody: {e.message}"
except Exception as err:
    import traceback
    res = traceback.format_exc()

with open('debug_out.txt', 'w', encoding='utf-8') as f:
    f.write(res)
