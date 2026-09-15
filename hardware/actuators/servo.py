import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO = None
    GPIO_AVAILABLE = False

from hardware.config import PIN_SERVO_MOTOR
from hardware.sensors.environment import consume_treat_in_simulation

# 라즈베리파이 BCM 핀 매핑 (GrovePi D5는 일반적으로 BCM 5번 또는 GPIO 핀에 매핑됨)
SERVO_GPIO_PIN = 5


def dispense_treat(amount=1):
    """
    SG-90 서보모터를 180도 회전시켜 간식을 배출하고 원위치(0도)로 복귀시킵니다.
    """
    print(f"\n🍖 [Actuator] 원격 간식 투출 동작 시작 (요청 수량: {amount}회)...")

    if GPIO_AVAILABLE and GPIO is not None:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(SERVO_GPIO_PIN, GPIO.OUT)
            pwm = GPIO.PWM(SERVO_GPIO_PIN, 50)  # 50Hz (20ms 주기)
            pwm.start(2.5)  # 0도 (닫힘 상태)
            time.sleep(0.3)

            for i in range(amount):
                # 180도 회전 (간식 배출구 열림)
                pwm.ChangeDutyCycle(12.5)
                time.sleep(0.7)
                # 0도 복귀 (간식 배출구 닫힘)
                pwm.ChangeDutyCycle(2.5)
                time.sleep(0.5)

            pwm.stop()
            GPIO.cleanup(SERVO_GPIO_PIN)
            print("✅ [Actuator] SG-90 서보모터 동작 완료!")
            return True
        except Exception as e:
            print(f"❌ [Actuator Error] 서보모터 구동 실패: {e}")
            return False

    # 가상 시뮬레이션 모드 (맥북 / 개발 환경)
    print("🔄 [SG-90 Servo SIM] 간식 배출구 열림 (180도 회전 중...)")
    time.sleep(0.7)
    print("🍖 [SG-90 Servo SIM] 간식 알갱이 투출 성공!")
    consume_treat_in_simulation(amount * 5)
    time.sleep(0.5)
    print("🔒 [SG-90 Servo SIM] 간식 배출구 닫힘 (0도 복귀 완료)")
    return True
