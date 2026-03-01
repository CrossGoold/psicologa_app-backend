"""Firebase notification service for push messages."""
import os
from django.conf import settings

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    
    # Initialize Firebase (requires FIREBASE_CREDENTIALS_PATH env var or credentials.json in project root)
    if not firebase_admin._apps:
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Firebase not initialized: {e}")


def send_notification(token: str, title: str, body: str, data: dict = None):
    """Send a push notification to a device."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        print(f"Error sending notification: {e}")
        return None


def send_notification_to_user(user_id: int, title: str, body: str, data: dict = None):
    """Send notification to all devices of a user."""
    from django.contrib.auth import get_user_model
    from .models import DeviceToken
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        tokens = DeviceToken.objects.filter(user=user).values_list('token', flat=True)
        for token in tokens:
            send_notification(token, title, body, data)
    except User.DoesNotExist:
        pass
