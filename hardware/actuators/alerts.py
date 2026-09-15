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


_night_led_state = False

def update_night_soothing_led(light_level: int, threshold: int = 150) -> bool:
    """
    실내 조도(Lux)에 따라 야간 안심 조명(D7 LED)을 자동으로 켜거나 끕니다.
    히스테리시스(30 Lux 마진)를 적용하여 경계값에서 조명이 깜빡이는 현상을 방지합니다.
    """
    global _night_led_state
    if light_level < threshold and not _night_led_state:
        _night_led_state = True
        set_status_led(True)
        print(f"💡 [Night LED] 실내 어두움 감지 ({light_level}Lux < {threshold}Lux) ➔ 야간 안심 조명 자동 점등 (ON)")
    elif light_level > (threshold + 30) and _night_led_state:
        _night_led_state = False
        set_status_led(False)
        print(f"💡 [Night LED] 실내 밝아짐 감지 ({light_level}Lux > {threshold+30}Lux) ➔ 야간 안심 조명 자동 소등 (OFF)")
    return _night_led_state

def get_night_led_status() -> bool:
    """현재 야간 안심 조명 켜짐 여부 반환"""
    return _night_led_state

