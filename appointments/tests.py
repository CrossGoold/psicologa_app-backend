from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Appointment
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

User = get_user_model()


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='pass')

    def test_unique_time(self):
        time = timezone.now()
        Appointment.objects.create(patient=self.user, scheduled_time=time)
        with self.assertRaises(Exception):
            Appointment.objects.create(patient=self.user, scheduled_time=time)


class AppointmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser', password='pass', email='patient@example.com')
        self.client.force_authenticate(self.user)
        # create a doctor user for staff tests
        self.doctor = User.objects.create_user(username='dr', password='docpass', email='dr@example.com', is_staff=True)

    def test_create_and_confirm(self):
        time = timezone.now()
        from django.core import mail

        # patch push notification so we can inspect
        with patch('appointments.views.send_notification_to_user') as mock_push:
            resp = self.client.post('/api/appointments/appointments/', {'scheduled_time': time.isoformat()})
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            # an email should have been sent to doctor
            self.assertEqual(len(mail.outbox), 1)
            appt = resp.data
            # list should return 1 for this user
            list_resp = self.client.get('/api/appointments/appointments/')
            self.assertEqual(len(list_resp.data), 1)
            # confirm
            confirm_resp = self.client.post(f"/api/appointments/appointments/{appt['id']}/confirm/")
            self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(confirm_resp.data['status'], 'confirmed')
            # another email to patient
            self.assertEqual(len(mail.outbox), 2)
            # verify push called for patient (last call)
            called_args = mock_push.call_args[0]
            self.assertEqual(called_args[0], self.user.id)
            self.assertEqual(called_args[1], 'Consulta Confirmada')
            self.assertIn('Sua consulta em', called_args[2])

    def test_staff_sees_all(self):
        time = timezone.now()
        self.client.post('/api/appointments/appointments/', {'scheduled_time': time.isoformat()})
        # switch to doctor and list
        self.client.force_authenticate(self.doctor)
        resp = self.client.get('/api/appointments/appointments/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_staff_can_confirm_any(self):
        time = timezone.now()
        post = self.client.post('/api/appointments/appointments/', {'scheduled_time': time.isoformat()})
        appt = post.data
        # staff confirm
        self.client.force_authenticate(self.doctor)
        confirm_resp = self.client.post(f"/api/appointments/appointments/{appt['id']}/confirm/")
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)

    def test_availabilities(self):
        # no existing appointments => slots returned
        start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        end = start + timezone.timedelta(hours=4)
        resp = self.client.get('/api/appointments/availabilities/', {'start': start.isoformat(), 'end': end.isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertIn('available', data)
        self.assertGreater(len(data['available']), 0)
        # create appointment and see it disappear
        Appointment.objects.create(patient=self.user, scheduled_time=start)
        resp2 = self.client.get('/api/appointments/availabilities/', {'start': start.isoformat(), 'end': end.isoformat()})
        self.assertNotIn(start.isoformat(), resp2.data['available'])

    def test_statistics_endpoint(self):
        # create a couple of appointments
        now = timezone.now()
        Appointment.objects.create(patient=self.user, scheduled_time=now)
        Appointment.objects.create(patient=self.user, scheduled_time=now + timezone.timedelta(days=1), status='confirmed')
        # non-staff should be forbidden
        resp = self.client.get('/api/appointments/statistics/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # staff should see counts
        self.client.force_authenticate(self.doctor)
        resp2 = self.client.get('/api/appointments/statistics/')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertIn('total_requested', resp2.data)
        self.assertIn('total_confirmed', resp2.data)
        self.assertIn('total_cancelled', resp2.data)

    def test_cancel_and_reschedule_notifications(self):
        from django.core import mail
        with patch('appointments.views.send_notification_to_user') as mock_push:
            time = timezone.now()
            resp = self.client.post('/api/appointments/appointments/', {'scheduled_time': time.isoformat()})
            appt = resp.data
            # cancel
            cancel = self.client.post(f"/api/appointments/appointments/{appt['id']}/cancel/")
            self.assertEqual(cancel.status_code, status.HTTP_200_OK)
            # push called at least once (patient or doctor)
            self.assertTrue(mock_push.called)
            # reschedule
            new_time = (time + timezone.timedelta(days=2)).isoformat()
            respR = self.client.post(f"/api/appointments/appointments/{appt['id']}/reschedule/", {'scheduled_time': new_time})
            self.assertEqual(respR.status_code, status.HTTP_200_OK)
            self.assertTrue(mock_push.called)


    def test_device_token_crud(self):
        token_str = 'abcd1234'
        # create device token
        resp = self.client.post('/api/appointments/device-tokens/', {'token': token_str})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        obj_id = resp.data['id']
        # list should return one
        list_resp = self.client.get('/api/appointments/device-tokens/')
        self.assertEqual(len(list_resp.data), 1)
        # delete it
        del_resp = self.client.delete(f'/api/appointments/device-tokens/{obj_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        list_resp2 = self.client.get('/api/appointments/device-tokens/')
        self.assertEqual(len(list_resp2.data), 0)
