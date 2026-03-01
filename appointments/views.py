from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.db import IntegrityError
from .models import Appointment, DeviceToken
from .serializers import AppointmentSerializer, DeviceTokenSerializer
from .notification_service import send_notification_to_user
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_datetime, parse_date
import datetime


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def availabilities(request):
    """Return available datetime slots between start and end query params."""
    start = request.query_params.get('start')
    end = request.query_params.get('end')
    if not start or not end:
        return Response({'error': 'start and end parameters required'}, status=status.HTTP_400_BAD_REQUEST)
    # parse input
    try:
        start_dt = parse_datetime(start) or parse_date(start)
        end_dt = parse_datetime(end) or parse_date(end)
    except Exception:
        return Response({'error': 'invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
        start_dt = datetime.datetime.combine(start_dt, datetime.time.min)
    if isinstance(end_dt, datetime.date) and not isinstance(end_dt, datetime.datetime):
        end_dt = datetime.datetime.combine(end_dt, datetime.time.max)
    # generate slots every hour within business hours 9-17
    slots = []
    cursor = start_dt
    while cursor <= end_dt:
        if 9 <= cursor.hour < 17:
            slots.append(cursor.isoformat())
        cursor += datetime.timedelta(hours=1)
    # exclude booked
    booked = Appointment.objects.filter(scheduled_time__gte=start_dt, scheduled_time__lte=end_dt).values_list('scheduled_time', flat=True)
    booked_set = set([b.isoformat() for b in booked])
    free = [s for s in slots if s not in booked_set]
    return Response({'available': free})


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # patients see only their own appointments; staff (doctor) see all
        if self.request.user.is_staff:
            return Appointment.objects.all()
        return Appointment.objects.filter(patient=self.request.user)

    # confirm action should probably be performed by staff

    def perform_create(self, serializer):
        try:
            appt = serializer.save(patient=self.request.user)
        except IntegrityError:
            raise serializers.ValidationError("This time slot is already booked.")
        # send email notification to doctor
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject="Novo agendamento solicitado",
            message=f"Paciente {self.request.user.username} solicitou consulta em {appt.scheduled_time}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DOCTOR_EMAIL],
        )
        # push notification to doctor if they have device tokens
        # assuming doctor user object exists and DOCTOR_EMAIL corresponds
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            doctor = User.objects.get(email=settings.DOCTOR_EMAIL)
            send_notification_to_user(
                doctor.id,
                "Novo agendamento",
                f"Paciente {self.request.user.username} marcou consulta para {appt.scheduled_time}."
            )
        except User.DoesNotExist:
            pass

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        # only allow if doctor or the patient themselves (maybe)
        appointment = self.get_object()
        if not request.user.is_staff and appointment.patient != request.user:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        appointment.status = 'confirmed'
        appointment.save()
        # notify patient by email
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject="Consulta confirmada",
            message=f"Sua consulta em {appointment.scheduled_time} foi confirmada.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.patient.email or ''],
        )
        # push notification
        send_notification_to_user(
            appointment.patient.id,
            "Consulta Confirmada",
            f"Sua consulta em {appointment.scheduled_time} foi confirmada."
        )
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        # notify patient via push and email optionally
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject="Consulta cancelada",
            message=f"Sua consulta em {appointment.scheduled_time} foi cancelada.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.patient.email or ''],
        )
        send_notification_to_user(
            appointment.patient.id,
            "Consulta Cancelada",
            f"Sua consulta em {appointment.scheduled_time} foi cancelada."
        )
        # inform doctor about cancellation
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            doctor = User.objects.get(email=settings.DOCTOR_EMAIL)
            send_notification_to_user(
                doctor.id,
                "Consulta Cancelada",
                f"Paciente {appointment.patient.username} cancelou consulta de {appointment.scheduled_time}."
            )
            send_mail(
                subject="Consulta cancelada",
                message=f"Paciente {appointment.patient.username} cancelou a consulta de {appointment.scheduled_time}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DOCTOR_EMAIL],
            )
        except User.DoesNotExist:
            pass
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        new_time = request.data.get('scheduled_time')
        if new_time:
            old_time = appointment.scheduled_time
            appointment.scheduled_time = new_time
            try:
                appointment.save()
            except IntegrityError:
                return Response({'error': 'Time slot not available.'}, status=status.HTTP_400_BAD_REQUEST)
            # notify patient
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject="Consulta reagendada",
                message=f"Sua consulta foi movida de {old_time} para {new_time}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.email or ''],
            )
            send_notification_to_user(
                appointment.patient.id,
                "Consulta Reagendada",
                f"Seu horário mudou de {old_time} para {new_time}."
            )
            # inform doctor
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                doctor = User.objects.get(email=settings.DOCTOR_EMAIL)
                send_notification_to_user(
                    doctor.id,
                    "Consulta Reagendada",
                    f"Paciente {appointment.patient.username} alterou consulta de {old_time} para {new_time}."
                )
                send_mail(
                    subject="Consulta reagendada",
                    message=f"Paciente {appointment.patient.username} mudou consulta de {old_time} para {new_time}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DOCTOR_EMAIL],
                )
            except User.DoesNotExist:
                pass
            return Response({'status': 'rescheduled'})
        return Response({'error': 'No new time provided'}, status=status.HTTP_400_BAD_REQUEST)

class DeviceTokenViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # users can only see/manage their own device tokens
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        # unregister device token
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def statistics(request):
    """Get appointment statistics (staff only)."""
    if not request.user.is_staff:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
    
    from django.utils import timezone
    today = timezone.now().date()
    
    total_requested = Appointment.objects.filter(status='requested').count()
    total_confirmed = Appointment.objects.filter(status='confirmed').count()
    total_cancelled = Appointment.objects.filter(status='cancelled').count()
    today_appts = Appointment.objects.filter(scheduled_time__date=today).count()
    
    return Response({
        'total_requested': total_requested,
        'total_confirmed': total_confirmed,
        'total_cancelled': total_cancelled,
        'today_appointments': today_appts,
    })