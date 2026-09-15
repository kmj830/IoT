import os
import firebase_admin
from firebase_admin import credentials, messaging

_fcm_initialized = False

def init_firebase():
    global _fcm_initialized
    if _fcm_initialized or firebase_admin._apps:
        _fcm_initialized = True
        return True
    
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "secrets/firebase-key.json")
    if not os.path.isabs(cred_path):
        cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cred_path)
    if os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _fcm_initialized = True
            return True
        except Exception as e:
            print(f"[FCM Init Error with Certificate] {e}")
    
    try:
        firebase_admin.initialize_app()
        _fcm_initialized = True
        return True
    except Exception as e:
        print(f"[FCM Default Init Error] {e}")
        return False

def send_bark_alert(device_id: str, sound_db: int, confidence: float, image_url: str = ""):
    """
    반려견 이상 짖음 감지 시 보호자 스마트폰으로 FCM 긴급 푸시 알림을 전송합니다.
    """
    if not init_firebase():
        print("[FCM] Firebase가 초기화되지 않아 푸시 전송을 건너뜁니다.")
        return None
    
    try:
        topic = f"dogmate_{device_id.replace('-', '_')}"
        conf_percent = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        
        message = messaging.Message(
            notification=messaging.Notification(
                title="🚨 [멍메이트 경보] 반려견 이상 짖음 감지!",
                body=f"소음 {sound_db}dB (AI 신뢰도 {conf_percent}%). 현장 사진을 확인하세요.",
                image=image_url if image_url else None
            ),
            data={
                "type": "BARK_ALERT",
                "device_id": str(device_id),
                "sound_db": str(sound_db),
                "confidence": str(confidence),
                "image_url": str(image_url)
            },
            topic=topic
        )
        response = messaging.send(message)
        print(f"[FCM] 푸시 알림 전송 성공 (Topic: {topic}, ID: {response})")
        return response
    except Exception as e:
        print(f"[FCM Send Error] {e}")
        return None
