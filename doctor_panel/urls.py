from django.urls import path
from . import views

app_name = 'doctor_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='confirm'),
    path('appointments/<int:appointment_id>/reject/', views.reject_appointment, name='reject'),
    path('statistics/', views.statistics, name='statistics'),
]
