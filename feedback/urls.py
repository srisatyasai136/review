from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_user, name='login_user'),
    path('register/', views.register_user, name='register_user'),
    path('logout/', views.logout_user, name='logout_user'),

    path('classes/', views.demo_class_list, name='demo_class_list'),
    path('class/<int:demo_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('class/<int:demo_id>/thank-you/', views.feedback_thank_you, name='feedback_thank_you'),
    path('staff/summary/', views.feedback_summary, name='feedback_summary'),

    # OTP and password reset
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    

]
