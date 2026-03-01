from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from appointments.models import Appointment
from django.utils import timezone
from datetime import timedelta
import json


def is_doctor(user):
    """Check if user is a doctor/staff."""
    return user.is_staff


@login_required
@user_passes_test(is_doctor)
def dashboard(request):
    """Doctor dashboard showing all appointments."""
    # Filter by status if provided
    status_filter = request.GET.get('status', 'requested')  # default: showing pending
    
    appointments = Appointment.objects.all().order_by('-scheduled_time')
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter)
    
    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'status_choices': ['requested', 'confirmed', 'cancelled', 'all'],
    }
    return render(request, 'doctor_panel/dashboard.html', context)


@login_required
@user_passes_test(is_doctor)
def confirm_appointment(request, appointment_id):
    """Confirm an appointment (AJAX)."""
    if request.method == 'POST':
        try:
            appt = Appointment.objects.get(id=appointment_id)
            appt.status = 'confirmed'
            appt.save()
            
            # Send notification to patient
            from appointments.notification_service import send_notification_to_user
            send_notification_to_user(
                appt.patient.id,
                'Consulta Confirmada',
                f'Sua consulta em {appt.scheduled_time} foi confirmada!'
            )
            
            return JsonResponse({'status': 'confirmed'})
        except Appointment.DoesNotExist:
            return JsonResponse({'error': 'Appointment not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=400)


@login_required
@user_passes_test(is_doctor)
def reject_appointment(request, appointment_id):
    """Reject/cancel an appointment (AJAX)."""
    if request.method == 'POST':
        try:
            appt = Appointment.objects.get(id=appointment_id)
            appt.status = 'cancelled'
            appt.save()
            
            # Notify patient
            from appointments.notification_service import send_notification_to_user
            send_notification_to_user(
                appt.patient.id,
                'Consulta Cancelada',
                f'Sua consulta em {appt.scheduled_time} foi cancelada.'
            )
            
            return JsonResponse({'status': 'cancelled'})
        except Appointment.DoesNotExist:
            return JsonResponse({'error': 'Appointment not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=400)


@login_required
@user_passes_test(is_doctor)
def statistics(request):
    """Get appointment statistics (AJAX)."""
    today = timezone.now().date()
    
    total_requested = Appointment.objects.filter(status='requested').count()
    total_confirmed = Appointment.objects.filter(status='confirmed').count()
    total_cancelled = Appointment.objects.filter(status='cancelled').count()
    
    today_appts = Appointment.objects.filter(scheduled_time__date=today).count()
    
    return JsonResponse({
        'total_requested': total_requested,
        'total_confirmed': total_confirmed,
        'total_cancelled': total_cancelled,
        'today_appointments': today_appts,
    })
