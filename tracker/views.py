import base64
import re
import csv
import logging
import imaplib
import email as email_lib
import email.header
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, Http404, JsonResponse
from django.views import View
from django.views.generic import CreateView, FormView, ListView, DetailView, TemplateView
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db.models import Q, F, Count, Max
import json
import datetime
import requests
from django.db.models.functions import TruncDate
from allauth.socialaccount.models import SocialToken

from .models import Email, EmailOpen
from .forms import UserRegisterForm, EmailForm, UserLoginForm
from django.contrib.auth.models import User

# Initialize Logger
logger = logging.getLogger('tracker')

# --- Helper Functions ---

def parse_user_agent(ua_string):
    """
    Parses a raw User-Agent string to return a user-friendly browser and OS representation.
    """
    if not ua_string:
        return "Unknown Browser", "Unknown OS"
    
    ua_lower = ua_string.lower()
    
    # OS Detection
    os_name = "Unknown OS"
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "linux" in ua_lower:
        os_name = "Linux"
        
    # Browser Detection
    browser = "Unknown Browser"
    if "chrome" in ua_lower or "chromium" in ua_lower:
        if "edg" in ua_lower:
            browser = "Edge"
        elif "opr" in ua_lower or "opera" in ua_lower:
            browser = "Opera"
        else:
            browser = "Chrome"
    elif "safari" in ua_lower:
        if "chrome" not in ua_lower:
            browser = "Safari"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "trident" in ua_lower or "msie" in ua_lower:
        browser = "Internet Explorer"
        
    return browser, os_name


# --- Authentication Views ---

class RegisterView(CreateView):
    """
    Handles user registration and redirects to login on success.
    """
    form_class = UserRegisterForm
    template_name = 'tracker/register.html'
    success_url = reverse_lazy('tracker:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        logger.info(f"New user registered successfully: '{username}'")
        messages.success(self.request, "Account created successfully! You can now log in.")
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('tracker:dashboard')
        return super().dispatch(request, *args, **kwargs)


class UserLoginView(LoginView):
    """
    Handles user login using Django's built-in session authentication.
    """
    template_name = 'tracker/login.html'
    form_class = UserLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(f"User '{self.request.user.username}' logged in successfully.")
        return response

    def form_invalid(self, form):
        username = self.request.POST.get('username', 'Unknown')
        logger.warning(f"Failed login attempt for username: '{username}'")
        if username != 'Unknown' and not User.objects.filter(username=username).exists():
            messages.error(self.request, "This username is not registered. Please register first.")
        else:
            messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class UserLogoutView(View):
    """
    Handles user logout securely. Requires POST requests to prevent CSRF.
    GET requests render a logout confirmation page.
    """
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, 'tracker/logout_confirm.html')
        return redirect('tracker:login')

    def post(self, request):
        username = request.user.username if request.user.is_authenticated else 'Anonymous'
        logout(request)
        logger.info(f"User '{username}' logged out successfully.")
        messages.success(request, "You have been logged out successfully.")
        return redirect('tracker:login')


# --- Core Functional Views ---

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Displays the aggregated analytics dashboard and recent email opens activity feed.
    """
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Core Metrics optimized with single-query aggregation
        stats = Email.objects.filter(user=user).aggregate(
            total_sent=Count('id'),
            opened_count=Count('id', filter=Q(open_count__gt=0))
        )
        total_sent = stats['total_sent'] or 0
        opened_count = stats['opened_count'] or 0
        unopened_count = total_sent - opened_count
        
        # Open Rate
        open_rate = round((opened_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        
        # Today's Opens
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_opens = EmailOpen.objects.filter(email__user=user, opened_at__gte=today_start).count()

        # Recent Activity Timeline (Last 5 Open events)
        recent_opens = EmailOpen.objects.filter(email__user=user).select_related('email').order_by('-opened_at')[:5]
        
        # Map user agent browser information dynamically
        for open_event in recent_opens:
            browser, os_name = parse_user_agent(open_event.user_agent)
            open_event.browser = browser
            open_event.os = os_name

        # Weekly Open Trends for last 7 days (including today)
        seven_days_ago = timezone.now() - datetime.timedelta(days=7)
        weekly_data = EmailOpen.objects.filter(
            email__user=user,
            opened_at__gte=seven_days_ago
        ).annotate(
            date=TruncDate('opened_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # Build 7-day structure (even for dates with 0 opens)
        today_date = timezone.now().date()
        weekly_trends = []
        weekly_labels = []
        for i in range(6, -1, -1):
            d = today_date - datetime.timedelta(days=i)
            weekly_labels.append(d.strftime('%a'))  # e.g., 'Mon', 'Tue'
            day_count = next((item['count'] for item in weekly_data if item['date'] == d), 0)
            weekly_trends.append(day_count)

        context.update({
            'total_sent': total_sent,
            'opened_count': opened_count,
            'unopened_count': unopened_count,
            'open_rate': open_rate,
            'today_opens': today_opens,
            'recent_opens': recent_opens,
            'weekly_labels_json': json.dumps(weekly_labels),
            'weekly_trends_json': json.dumps(weekly_trends),
            'active_tab': 'dashboard'
        })
        return context


class ComposeEmailView(LoginRequiredMixin, FormView):
    """
    Handles rich text email composition, pixel embedding, and background email dispatch.
    """
    template_name = 'tracker/compose.html'
    form_class = EmailForm
    success_url = reverse_lazy('tracker:email_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'compose'
        return context

    def form_valid(self, form):
        recipient = form.cleaned_data['recipient']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        # Create record first to generate tracking UUID
        email_obj = Email(
            user=self.request.user,
            recipient=recipient,
            subject=subject,
            message=message
        )
        email_obj.save()

        # Build absolute URL pointing to Tracking Endpoint
        site_url = getattr(settings, 'SITE_URL', '')
        if site_url:
            tracking_path = reverse('tracker:track', args=[email_obj.tracking_id])
            tracking_url = f"{site_url.rstrip('/')}{tracking_path}"
        else:
            tracking_url = self.request.build_absolute_uri(
                reverse('tracker:track', args=[email_obj.tracking_id])
            )

        # Inject hidden tracking pixel tag at the end of the HTML body
        tracking_pixel_tag = f'<img src="{tracking_url}" width="1" height="1" alt="" style="display: none; border: 0; outline: none;" />'
        tracked_message_html = f"{message}\n{tracking_pixel_tag}"

        # Setup plain text alternative by stripping HTML tags
        plain_text = strip_tags(message)

        # Collect uploaded file attachments
        uploaded_files = self.request.FILES.getlist('attachments')

        # Dispatch Multi-Alternative Email
        try:
            import mimetypes
            from_email = settings.EMAIL_HOST_USER or 'noreply@mailpulse.com'
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=from_email,
                to=[recipient]
            )
            msg.attach_alternative(tracked_message_html, "text/html")

            # Attach uploaded files
            for uploaded_file in uploaded_files:
                mime_type, _ = mimetypes.guess_type(uploaded_file.name)
                mime_type = mime_type or 'application/octet-stream'
                msg.attach(uploaded_file.name, uploaded_file.read(), mime_type)

            # Instead of SMTP, send using Gmail REST API to bypass firewall blocks
            social_token = SocialToken.objects.filter(account__user=self.request.user, account__provider='google').first()
            if not social_token:
                raise Exception("Google Account not fully connected. Please log out and log back in to grant Gmail access.")
            
            raw_message = msg.message().as_bytes()
            encoded_message = base64.urlsafe_b64encode(raw_message).decode('utf-8')
            
            payload = {'raw': encoded_message}
            headers = {
                'Authorization': f'Bearer {social_token.token}', 
                'Content-Type': 'application/json'
            }
            
            api_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
            response = requests.post(api_url, json=payload, headers=headers)
            
            if response.status_code not in (200, 201):
                if response.status_code == 401:
                    raise Exception("Your Google Login session expired. Please log out and log back in.")
                raise Exception(f"Gmail API Error: {response.text}")

            attach_info = f" with {len(uploaded_files)} attachment(s)" if uploaded_files else ""
            logger.info(f"Email '{email_obj.tracking_id}' successfully dispatched from '{self.request.user.username}' to '{recipient}'{attach_info}")
            messages.success(self.request, f"Email successfully sent and tracked to {recipient}{attach_info}!")
        except Exception as e:
            logger.error(f"Error sending email '{email_obj.tracking_id}' to '{recipient}': {str(e)}", exc_info=True)
            # Delete saved model since the mail delivery operation failed
            email_obj.delete()
            messages.error(self.request, f"Failed to send email. SMTP Error: {str(e)}")
            # Return form populated with errors
            return self.form_invalid(form)

        return super().form_valid(form)



class EmailListView(LoginRequiredMixin, ListView):
    """
    Displays the list of sent emails with support for pagination, searching, sorting, and status filtering.
    """
    template_name = 'tracker/email_list.html'
    context_object_name = 'emails'
    paginate_by = 10

    def get_queryset(self):
        queryset = Email.objects.filter(user=self.request.user).annotate(
            last_opened=Max('opens__opened_at')
        )
        
        # Searching
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(Q(recipient__icontains=q) | Q(subject__icontains=q))
            
        # Status Filtering
        status_filter = self.request.GET.get('status', 'all')
        if status_filter == 'opened':
            queryset = queryset.filter(open_count__gt=0)
        elif status_filter == 'unopened':
            queryset = queryset.filter(open_count=0)

        # Sorting
        sort = self.request.GET.get('sort', 'desc')
        if sort == 'asc':
            queryset = queryset.order_by('sent_at')
        else:
            queryset = queryset.order_by('-sent_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'q': self.request.GET.get('q', ''),
            'status': self.request.GET.get('status', 'all'),
            'sort': self.request.GET.get('sort', 'desc'),
            'active_tab': 'emails'
        })
        return context


class EmailDetailView(LoginRequiredMixin, DetailView):
    """
    Displays detail tracking analytics, history metrics, and parsed open logs for a single email.
    """
    model = Email
    template_name = 'tracker/email_detail.html'
    context_object_name = 'email'
    slug_field = 'tracking_id'
    slug_url_kwarg = 'tracking_id'

    def get_queryset(self):
        # Prevent users from viewing other people's emails
        return Email.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        email = self.object
        
        # Open history ordered by latest
        opens = email.opens.all().order_by('-opened_at')
        
        # Parse User Agents dynamically for clean display
        parsed_opens = []
        for o in opens:
            browser, os_name = parse_user_agent(o.user_agent)
            parsed_opens.append({
                'opened_at': o.opened_at,
                'ip_address': o.ip_address,
                'browser': browser,
                'os': os_name,
                'raw_ua': o.user_agent
            })
            
        context.update({
            'opens_history': parsed_opens,
            'active_tab': 'emails'
        })
        return context


class UserProfileView(LoginRequiredMixin, TemplateView):
    """
    Displays the user profile details and overall user stats.
    """
    template_name = 'tracker/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        total_emails = Email.objects.filter(user=user).count()
        total_opens = EmailOpen.objects.filter(email__user=user).count()
        
        # Last 5 dispatched emails
        recent_emails = Email.objects.filter(user=user).order_by('-sent_at')[:5]
        
        context.update({
            'total_emails': total_emails,
            'total_opens': total_opens,
            'recent_emails': recent_emails,
            'active_tab': 'profile'
        })
        return context


class ExportCSVView(LoginRequiredMixin, View):
    """
    Generates and downloads a CSV tracking report of the user's sent emails.
    """
    def get(self, request, *args, **kwargs):
        logger.info(f"User '{request.user.username}' initiated CSV report download")
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="mailpulse_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Recipient Email', 'Subject', 'Sent Date (UTC)', 'Open Count', 'Last Opened Date (UTC)'])
        
        emails = Email.objects.filter(user=request.user).prefetch_related('opens')
        
        for email in emails:
            last_open = email.opens.order_by('-opened_at').first()
            last_opened_str = last_open.opened_at.strftime('%Y-%m-%d %H:%M:%S') if last_open else 'Never Opened'
            
            writer.writerow([
                email.recipient,
                email.subject,
                email.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
                email.open_count,
                last_opened_str
            ])
            
        return response


# --- Tracking Pixel Endpoint View ---

class TrackingPixelView(View):
    """
    Public pixel tracking endpoint requested by email clients.
    Logs the IP and User-Agent, increments total opens, and returns a transparent 1x1 PNG.
    """
    def get(self, request, tracking_id, *args, **kwargs):
        # Look up email by unique UUID
        try:
            email = Email.objects.get(tracking_id=tracking_id)
        except (Email.DoesNotExist, ValueError) as e:
            logger.warning(f"Invalid tracking ID request: '{tracking_id}'. Reference: {str(e)}")
            # Fail silently with a pixel even if ID is invalid to prevent breaking email renders
            return self._serve_pixel()

        # Capture Client IP Address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Capture Client User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Write EmailOpen event
        EmailOpen.objects.create(
            email=email,
            ip_address=ip,
            user_agent=user_agent
        )

        # Increment cached counter (using direct F-expression to avoid race condition writes)
        Email.objects.filter(id=email.id).update(open_count=F('open_count') + 1)
        
        logger.info(f"Email pixel '{tracking_id}' loaded. Open counted. Client IP: '{ip}'")

        return self._serve_pixel()

    def _serve_pixel(self):
        # Base64 string representing a 1x1 transparent PNG
        PNG_DATA = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        )
        response = HttpResponse(PNG_DATA, content_type='image/png')
        
        # Enforce strict Cache-Control headers to make sure requests reach our backend every time
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


# --- Live Status Polling API ---

class EmailStatusAPIView(LoginRequiredMixin, View):
    """
    JSON API endpoint for live polling of email open statuses.
    Returns a list of {tracking_id, open_count, is_opened, last_opened} for the current user's emails.
    """
    def get(self, request, *args, **kwargs):
        emails = Email.objects.filter(user=request.user).annotate(
            last_opened_at=Max('opens__opened_at')
        ).values('tracking_id', 'open_count', 'last_opened_at')

        data = []
        for e in emails:
            data.append({
                'tracking_id': str(e['tracking_id']),
                'open_count': e['open_count'],
                'is_opened': e['open_count'] > 0,
                'last_opened': e['last_opened_at'].strftime('%Y-%m-%d %H:%M') if e['last_opened_at'] else None,
            })
        return JsonResponse({'emails': data})


# --- Delete Email View ---

class DeleteEmailView(LoginRequiredMixin, View):
    """
    Deletes a single tracked email by tracking_id. Accepts POST for security.
    Returns JSON with success status so the front-end can animate the row removal.
    """
    def post(self, request, tracking_id, *args, **kwargs):
        email_obj = get_object_or_404(Email, tracking_id=tracking_id, user=request.user)
        subject = email_obj.subject
        email_obj.delete()
        logger.info(f"User '{request.user.username}' deleted email '{tracking_id}' (subject: '{subject}')")
        return JsonResponse({'success': True, 'message': f'Email "{subject}" deleted.'})


# --- Clear History View ---

class ClearHistoryView(LoginRequiredMixin, View):
    """
    Deletes ALL tracked emails for the current user.
    """
    def post(self, request, *args, **kwargs):
        count, _ = Email.objects.filter(user=request.user).delete()
        logger.info(f"User '{request.user.username}' cleared entire email history ({count} records deleted)")
        messages.success(request, f'All {count} tracked email(s) have been deleted.')
        return redirect('tracker:email_list')


# --- Inbox Viewer (IMAP) ---

def _decode_header_value(value):
    """Safely decodes MIME encoded email header strings."""
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


def _get_email_body(msg):
    """Extract plain text or HTML body from an email.Message object."""
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


def _html_to_plain_text(html):
    """Convert HTML to plain text with proper spacing between elements."""
    if not html:
        return ''
    # Replace block-level closing/opening tags with a space so words don't merge
    html = re.sub(r'</(p|div|li|td|th|br|h[1-6]|blockquote|pre)>', ' ', html, flags=re.IGNORECASE)
    html = re.sub(r'<br\s*/?>', ' ', html, flags=re.IGNORECASE)
    # Strip remaining tags
    text = strip_tags(html)
    # Normalize whitespace: collapse multiple spaces/newlines into single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class InboxView(LoginRequiredMixin, TemplateView):
    """
    Connects to the configured IMAP server and retrieves the latest received emails.
    """
    template_name = 'tracker/inbox.html'

    def get(self, request, *args, **kwargs):
        context = {'active_tab': 'inbox'}

        imap_host = getattr(settings, 'IMAP_HOST', '')
        imap_port = getattr(settings, 'IMAP_PORT', 993)
        imap_user = getattr(settings, 'EMAIL_HOST_USER', '')
        imap_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')

        if not imap_host or not imap_user or not imap_password:
            context['error'] = 'IMAP credentials are not configured. Please set IMAP_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD in your .env file.'
            context['inbox_emails'] = []
            return self.render_to_response(context)

        try:
            mail = imaplib.IMAP4_SSL(imap_host, int(imap_port))
            mail.login(imap_user, imap_password)
            mail.select('INBOX')

            # Search for all emails, get latest 25
            _, messages_data = mail.search(None, 'ALL')
            mail_ids = messages_data[0].split()
            latest_ids = mail_ids[-25:] if len(mail_ids) > 25 else mail_ids
            latest_ids = list(reversed(latest_ids))  # newest first

            inbox_emails = []
            for mail_id in latest_ids:
                try:
                    _, msg_data = mail.fetch(mail_id, '(RFC822)')
                    # msg_data[0] must be a tuple (header, raw_bytes); skip otherwise
                    if not msg_data or not isinstance(msg_data[0], tuple):
                        logger.warning(f"Unexpected IMAP fetch format for mail_id {mail_id}: {msg_data}")
                        continue
                    raw_email = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw_email)

                    # Parse flags
                    _, flag_data = mail.fetch(mail_id, '(FLAGS)')
                    flags = ''
                    if flag_data and flag_data[0]:
                        flags = flag_data[0].decode() if isinstance(flag_data[0], bytes) else str(flag_data[0])
                    is_read = '\\Seen' in flags

                    body_html = _get_email_body(msg)
                    inbox_emails.append({
                        'id': mail_id.decode(),
                        'from': _decode_header_value(msg.get('From', '')),
                        'subject': _decode_header_value(msg.get('Subject', '(No Subject)')),
                        'date': _decode_header_value(msg.get('Date', '')),
                        'body': body_html,
                        'body_preview': _html_to_plain_text(body_html)[:120],
                        'is_read': is_read,
                    })
                except Exception as per_mail_err:
                    logger.warning(f"Skipping mail_id {mail_id} due to parse error: {per_mail_err}")
                    continue

            mail.logout()
            context['inbox_emails'] = inbox_emails
            context['error'] = None
            logger.info(f"Inbox loaded {len(inbox_emails)} emails for user '{request.user.username}'")

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection error for user '{request.user.username}': {str(e)}")
            context['error'] = f'Failed to connect to inbox: {str(e)}. Please check your IMAP settings and App Password.'
            context['inbox_emails'] = []
        except Exception as e:
            logger.error(f"Unexpected inbox error for user '{request.user.username}': {str(e)}", exc_info=True)
            context['error'] = f'Unexpected error: {str(e)}'
            context['inbox_emails'] = []

        return self.render_to_response(context)

