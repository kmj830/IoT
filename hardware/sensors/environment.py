import random
import time

try:
    import grovepi
    GROVE_AVAILABLE = True
except (ImportError, RuntimeError):
    grovepi = None
    GROVE_AVAILABLE = False

from hardware.config import (
    PIN_DHT_SENSOR,
    PIN_LIGHT_SENSOR,
    PIN_ULTRASONIC_SENSOR,
    TREAT_CONTAINER_EMPTY_CM,
    TREAT_CONTAINER_FULL_CM
)

# 시뮬레이션용 상태값 저장 변수
_sim_temp = 24.0
_sim_hum = 50.0
_sim_light = 350
_sim_treat = 85


def read_temperature_humidity():
    """
    온습도 센서(DHT11 / D3)에서 온도(℃)와 습도(%)를 읽어옵니다.
    GrovePi 미연결 시 가상 시뮬레이션 데이터를 반환합니다.
    """
    global _sim_temp, _sim_hum
    if GROVE_AVAILABLE:
        try:
            # 0: DHT11 (파란색 센서), 1: DHT22 (흰색 센서)
            [temp, hum] = grovepi.dht(PIN_DHT_SENSOR, 0)
            if not (temp == -1 or hum == -1):
                return round(float(temp), 1), round(float(hum), 1)
        except Exception as e:
            print(f"[Sensor Error] DHT 온습도 읽기 실패: {e}")
    
    # 가상 시뮬레이션 모드 (현실적인 미세 변동 생성)
    _sim_temp += random.uniform(-0.3, 0.3)
    _sim_temp = max(18.0, min(32.0, _sim_temp))
    _sim_hum += random.uniform(-0.5, 0.5)
    _sim_hum = max(30.0, min(80.0, _sim_hum))
    return round(_sim_temp, 1), round(_sim_hum, 1)


def read_light_level():
    """
    조도 센서(A1)에서 아날로그 밝기 값(Lux)을 읽어옵니다.
    """
    global _sim_light
    if GROVE_AVAILABLE:
        try:
            val = grovepi.analogRead(PIN_LIGHT_SENSOR)
            return int(val)
        except Exception as e:
            print(f"[Sensor Error] 조도 센서 읽기 실패: {e}")
            
    # 가상 시뮬레이션 모드
    _sim_light += random.randint(-10, 10)
    _sim_light = max(100, min(800, _sim_light))
    return _sim_light


def read_treat_level_percent():
    """
    초음파 센서(D4)로 간식 상단과의 거리를 측정하여
    간식 잔여량 비율(0~100%)로 환산합니다.
    """
    global _sim_treat
    if GROVE_AVAILABLE:
        try:
            dist_cm = grovepi.ultrasonicRead(PIN_ULTRASONIC_SENSOR)
            # 유효 거리 클램핑
            clamped_dist = max(TREAT_CONTAINER_FULL_CM, min(TREAT_CONTAINER_EMPTY_CM, float(dist_cm)))
            # 비율 환산: 거리가 가까울수록 간식이 많이 남은 것
            pct = (TREAT_CONTAINER_EMPTY_CM - clamped_dist) / (TREAT_CONTAINER_EMPTY_CM - TREAT_CONTAINER_FULL_CM) * 100.0
            return max(0, min(100, int(round(pct))))
        except Exception as e:
            print(f"[Sensor Error] 초음파 센서 읽기 실패: {e}")

    # 가상 시뮬레이션 모드
    return _sim_treat


def consume_treat_in_simulation(amount_percent=5):
    """시뮬레이션 모드에서 간식 급여 시 잔여량을 차감하는 헬퍼 함수"""
    global _sim_treat
    _sim_treat = max(0, _sim_treat - amount_percent)
    return _sim_treat


def get_all_environment_telemetry():
    """
    주기적 텔레메트리 전송용 모든 센서 데이터를 한 번에 수집합니다.
    """
    temp, hum = read_temperature_humidity()
    light = read_light_level()
    treat = read_treat_level_percent()
    return {
        "temperature": temp,
        "humidity": hum,
        "light_level": light,
        "treat_percent": treat
    }
