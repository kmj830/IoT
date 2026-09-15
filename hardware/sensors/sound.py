import random
import time

try:
    import grovepi
    GROVE_AVAILABLE = True
except (ImportError, RuntimeError):
    grovepi = None
    GROVE_AVAILABLE = False

from hardware.config import PIN_SOUND_SENSOR, SOUND_ALERT_THRESHOLD


def read_sound_level():
    """
    Grove 사운드 센서(A0) 아날로그 값을 읽어와 실시간 데시벨(dB) 근사치(30~100dB)로 환산합니다.
    """
    if GROVE_AVAILABLE:
        try:
            val = grovepi.analogRead(PIN_SOUND_SENSOR)
            # Grove 사운드 센서 아날로그(0~1023) 값을 대략적인 dB(30~100)로 맵핑
            db = 30 + (val / 1023.0) * 70.0
            return int(round(db))
        except Exception as e:
            print(f"[Sensor Error] 사운드 센서 읽기 실패: {e}")

    # 가상 시뮬레이션: 평상시 40~55dB (조용한 실내)
    return random.randint(42, 54)


def detect_noise_spike(threshold_db=SOUND_ALERT_THRESHOLD):
    """
    설정된 데시벨 임계값(기본 70dB)을 초과하는 소음 급증이 감지되었는지 확인합니다.
    """
    current_db = read_sound_level()
    return current_db >= threshold_db, current_db
