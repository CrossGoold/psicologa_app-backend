from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/appointments/', include('appointments.urls')),
    path('api/users/', include('users.urls')),
    path('api/token-auth/', auth_views.obtain_auth_token),
    path('panel/', include('doctor_panel.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
