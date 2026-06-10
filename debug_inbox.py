import imaplib
import email as email_lib
import email.header
import traceback

def decode_header_value(value):
    if not value:
        return ''
    parts = email.header.decode_header(value)
    decoded_parts = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or 'utf-8', errors='replace'))
            except (LookupError, UnicodeDecodeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(str(part))
    return ' '.join(decoded_parts)

def get_email_body(msg):
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))
            if 'attachment' in disposition:
                continue
            if content_type == 'text/html':
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
            elif content_type == 'text/plain' and not body:
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='replace')
    return body

try:
    print("Connecting to IMAP...")
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    mail.login('keerthanam2027@mca.ajce.in', 'yrtq bokt lfkb puzv')
    print("Login OK")
    mail.select('INBOX')
    
    status, messages_data = mail.search(None, 'ALL')
    mail_ids = messages_data[0].split()
    print(f"Total emails: {len(mail_ids)}")
    
    latest_ids = mail_ids[-25:] if len(mail_ids) > 25 else mail_ids
    latest_ids = list(reversed(latest_ids))
    print(f"Fetching latest {len(latest_ids)} emails...")
    
    inbox_emails = []
    for i, mail_id in enumerate(latest_ids[:5]):  # test first 5
        try:
            print(f"\n[{i+1}] Fetching mail_id={mail_id}...")
            status, msg_data = mail.fetch(mail_id, '(RFC822)')
            print(f"  fetch status: {status}")
            print(f"  msg_data[0] type: {type(msg_data[0])}")
            
            raw_email = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)
            
            # Parse flags
            status2, flag_data = mail.fetch(mail_id, '(FLAGS)')
            flags = flag_data[0].decode() if flag_data[0] else ''
            is_read = '\\Seen' in flags
            
            from_val = decode_header_value(msg.get('From', ''))
            subject_val = decode_header_value(msg.get('Subject', '(No Subject)'))
            date_val = decode_header_value(msg.get('Date', ''))
            body_val = get_email_body(msg)
            
            inbox_emails.append({
                'id': mail_id.decode(),
                'from': from_val,
                'subject': subject_val,
                'date': date_val,
                'body': body_val[:100],
                'is_read': is_read,
            })
            print(f"  From: {from_val}")
            print(f"  Subject: {subject_val}")
            print(f"  Date: {date_val}")
            print(f"  is_read: {is_read}")
        except Exception as e:
            print(f"  ERROR on mail_id {mail_id}: {e}")
            traceback.print_exc()
    
    mail.logout()
    print(f"\n=== Final inbox_emails count: {len(inbox_emails)} ===")

except Exception as e:
    print(f"FATAL ERROR: {e}")
    traceback.print_exc()
