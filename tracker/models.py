import uuid
from django.db import models
from django.contrib.auth.models import User

class Email(models.Model):
    """
    Represents an outgoing tracked email.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emails')
    recipient = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()  # HTML content generated from Quill.js
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    open_count = models.PositiveIntegerField(default=0)  # Cached counter for optimization

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.recipient} - {self.subject[:30]}"

    @property
    def is_opened(self):
        return self.open_count > 0

    @property
    def open_rate(self):
        """
        For a single email, open rate is 100% if opened, else 0%.
        """
        return 100 if self.is_opened else 0


class EmailOpen(models.Model):
    """
    Records each individual open action on a sent email.
    """
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='opens')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"Open for {self.email.recipient} at {self.opened_at}"
