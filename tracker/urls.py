from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('compose/', views.ComposeEmailView.as_view(), name='compose'),
    path('emails/', views.EmailListView.as_view(), name='email_list'),
    path('email/<uuid:tracking_id>/', views.EmailDetailView.as_view(), name='email_detail'),
    path('email/<uuid:tracking_id>/delete/', views.DeleteEmailView.as_view(), name='email_delete'),
    path('emails/clear/', views.ClearHistoryView.as_view(), name='clear_history'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('export/', views.ExportCSVView.as_view(), name='export_csv'),
    path('track/<uuid:tracking_id>/', views.TrackingPixelView.as_view(), name='track'),
    path('inbox/', views.InboxView.as_view(), name='inbox'),
    # Live status polling API
    path('api/emails/status/', views.EmailStatusAPIView.as_view(), name='api_email_status'),
]
