from django.urls import path
from . import views
from core.views import create_buy_request

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.history, name='history'),
    path('buy/', views.buy_view, name='buy_level'),
    path('payment/', views.payment_view, name='payment'),
    path('finance/', views.finance_view, name='finance'),
    path('profile/', views.profile_view, name='profile'),
    path('api/create_buy_request/', views.create_buy_request, name='create_buy_request'),
    path('my-scooters/', views.my_scooters_view, name='my_scooters'),
    path('api/claim_profit/', views.claim_profit_view, name='claim_profit'),
    path('referral/', views.referral_view, name='referral'),
    path('settings/', views.settings_view, name='settings'),
    path('about/', views.about_view, name='about'),
    path('api/create_withdrawal_request/', views.create_withdrawal_request, name='create_withdrawal_request'),
    path('monitoring/', views.monitoring_view, name='monitoring'),

]
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
