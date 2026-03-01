from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, DeviceTokenViewSet, availabilities, statistics

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'device-tokens', DeviceTokenViewSet, basename='device-token')

urlpatterns = [
    path('availabilities/', availabilities),
    path('statistics/', statistics),
    path('', include(router.urls)),
]
