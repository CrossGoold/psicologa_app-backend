from rest_framework import serializers
from .models import Appointment, DeviceToken


class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.ReadOnlyField(source='patient.username')

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'scheduled_time', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'created_at']
        read_only_fields = ['created_at']
