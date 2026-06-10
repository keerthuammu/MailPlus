from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone

from .models import Email, EmailOpen

class MailPulseTestCase(TestCase):
    """
    Comprehensive test suite for MailPulse authentication, email tracking,
    dashboard logic, and report exports.
    """
    
    def setUp(self):
        # Create a test user
        self.username = 'testuser'
        self.password = 'securepassword123!'
        self.email = 'testuser@example.com'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email=self.email
        )
        
    # --- Authentication Tests ---

    def test_user_registration(self):
        """
        Tests registration form creation and user table inserts.
        """
        url = reverse('tracker:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'differentpassword123!',
            'password_confirm': 'differentpassword123!'
        }
        # Include fields matching the UserRegisterForm
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'differentpassword123!',
            'password_confirm': 'differentpassword123!'
        }
        
        # Standard UserCreationForm fields are password1 and password2
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'differentpassword123!',
            'password2': 'differentpassword123!',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_login(self):
        """
        Tests login form authentication and session keys.
        """
        url = reverse('tracker:login')
        data = {
            'username': self.username,
            'password': self.password
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tracker:dashboard'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_user_logout(self):
        """
        Tests session clearing, GET confirmation view, and POST logout redirection.
        """
        self.client.login(username=self.username, password=self.password)
        url = reverse('tracker:logout')
        
        # Check GET logout renders the confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/logout_confirm.html')
        self.assertTrue('_auth_user_id' in self.client.session)  # Still logged in
        
        # Check POST logout clears the session and redirects
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tracker:login'))
        self.assertFalse('_auth_user_id' in self.client.session)  # Logged out



    # --- Email Composition & SMTP Tests ---

    def test_compose_email(self):
        """
        Verifies rich email compose, tracking pixel injection, and mail outbox mock.
        """
        self.client.login(username=self.username, password=self.password)
        url = reverse('tracker:compose')
        data = {
            'recipient': 'recipient@example.com',
            'subject': 'Test Subject Line',
            'message': '<p>Hello world. This is a tracked email.</p>'
        }
        
        # Verify post redirects and model is created
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        email_record = Email.objects.filter(user=self.user).first()
        self.assertIsNotNone(email_record)
        self.assertEqual(email_record.recipient, 'recipient@example.com')
        self.assertEqual(email_record.subject, 'Test Subject Line')
        
        # Verify mock mailbox received the outgoing email
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertEqual(sent_mail.to, ['recipient@example.com'])
        self.assertEqual(sent_mail.subject, 'Test Subject Line')
        
        # Verify pixel HTML is embedded in alternative content
        self.assertEqual(len(sent_mail.alternatives), 1)
        html_content, content_type = sent_mail.alternatives[0]
        self.assertIn('/track/', html_content)
        self.assertIn(str(email_record.tracking_id), html_content)


    # --- Tracking Pixel System Tests ---

    def test_tracking_pixel_endpoint(self):
        """
        Asserts tracking logging details (IP, UA, counts) and PNG rendering.
        """
        # Create an email to track
        email_record = Email.objects.create(
            user=self.user,
            recipient='recipient@example.com',
            subject='Track Me',
            message='<p>Content</p>'
        )
        
        track_url = reverse('tracker:track', args=[email_record.tracking_id])
        
        # Trigger tracking hit with specific metadata
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'REMOTE_ADDR': '192.168.1.50'
        }
        
        response = self.client.get(track_url, **headers)
        
        # Refresh from database
        email_record.refresh_from_db()
        
        # Assert open logs creation
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(email_record.open_count, 1)
        
        # Assert database logs match request
        open_log = EmailOpen.objects.filter(email=email_record).first()
        self.assertIsNotNone(open_log)
        self.assertEqual(open_log.ip_address, '192.168.1.50')
        self.assertEqual(open_log.user_agent, headers['HTTP_USER_AGENT'])
        
        # Assert Cache-Control policies
        self.assertEqual(response['Cache-Control'], 'no-cache, no-store, must-revalidate, private, max-age=0')
        self.assertEqual(response['Pragma'], 'no-cache')
        self.assertEqual(response['Expires'], '0')


    # --- Dashboard Metrics Tests ---

    def test_dashboard_statistics(self):
        """
        Validates aggregate calculations logic on the dashboard.
        """
        # 1. Setup email data
        # Email 1: Opened once
        email1 = Email.objects.create(
            user=self.user, recipient='e1@example.com', subject='Sub1', message='msg', open_count=1
        )
        EmailOpen.objects.create(email=email1, ip_address='1.1.1.1', user_agent='UA')

        # Email 2: Unopened
        Email.objects.create(
            user=self.user, recipient='e2@example.com', subject='Sub2', message='msg', open_count=0
        )

        # Login and call dashboard
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('tracker:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        context = response.context
        
        self.assertEqual(context['total_sent'], 2)
        self.assertEqual(context['opened_count'], 1)
        self.assertEqual(context['unopened_count'], 1)
        self.assertEqual(context['open_rate'], 50.0)
        self.assertEqual(context['today_opens'], 1)


    # --- CSV Export Tests ---

    def test_csv_export(self):
        """
        Validates CSV content stream layout.
        """
        # Create an email record
        Email.objects.create(
            user=self.user, recipient='export@example.com', subject='Export Sub', message='msg', open_count=3
        )
        
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('tracker:export_csv'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="mailpulse_report_', response['Content-Disposition'])
        
        # Read the CSV content
        content = response.content.decode('utf-8')
        lines = content.splitlines()
        
        # Verify columns header
        self.assertEqual(lines[0], 'Recipient Email,Subject,Sent Date (UTC),Open Count,Last Opened Date (UTC)')
        # Verify row content
        self.assertIn('export@example.com', lines[1])
        self.assertIn('Export Sub', lines[1])
        self.assertIn('3', lines[1])

    def test_unregistered_user_login(self):
        """
        Tests that an unregistered user cannot log in and receives a clear error message.
        """
        url = reverse('tracker:login')
        data = {
            'username': 'nonexistentuser',
            'password': 'somepassword123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)  # Re-renders login page on form invalid
        
        # Verify the custom unregistered user message is present in the messages framework
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "This username is not registered. Please register first.")
