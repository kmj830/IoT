import time

try:
    import grovepi
    GROVE_AVAILABLE = True
except (ImportError, RuntimeError):
    grovepi = None
    GROVE_AVAILABLE = False

from hardware.config import PIN_BUZZER, PIN_LED


def trigger_alert_beep(duration_sec=0.5):
    """
    부저(D6)를 짧게 울려 경보음 또는 알림음을 출력합니다.
    """
    if GROVE_AVAILABLE:
        try:
            grovepi.pinMode(PIN_BUZZER, "OUTPUT")
            grovepi.digitalWrite(PIN_BUZZER, 1)
            time.sleep(duration_sec)
            grovepi.digitalWrite(PIN_BUZZER, 0)
            return True
        except Exception as e:
            print(f"[Actuator Error] 부저 제어 실패: {e}")

    print(f"🔔 [Buzzer SIM] 삐-익! (경보음 {duration_sec}초)")
    return True


def set_status_led(state: bool):
    """
    상태 표시 LED(D7)를 켜거나(True) 끕니다(False).
    """
    if GROVE_AVAILABLE:
        try:
            grovepi.pinMode(PIN_LED, "OUTPUT")
            grovepi.digitalWrite(PIN_LED, 1 if state else 0)
            return True
        except Exception as e:
            print(f"[Actuator Error] LED 제어 실패: {e}")

    # print(f"💡 [LED SIM] 상태: {'ON' if state else 'OFF'}")
    return True
