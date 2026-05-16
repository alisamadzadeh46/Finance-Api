from django.urls import path
from users import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),

    # Profile
    path('profile/', views.UserView.as_view(), name='profile'),

    # KYC
    path('kyc/', views.KYCSubmitView.as_view(), name='kyc'),
    path('kyc/admin/', views.KYCAdminReviewView.as_view(), name='kyc-admin-list'),
    path('kyc/admin/<int:pk>/', views.KYCAdminDetailView.as_view(), name='kyc-admin-detail'),

    # Transaction PIN
    path('pin/set/', views.SetPINView.as_view(), name='pin-set'),
    path('pin/change/', views.ChangePINView.as_view(), name='pin-change'),
    path('pin/verify/', views.VerifyPINView.as_view(), name='pin-verify'),
]
