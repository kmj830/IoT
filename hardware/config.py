import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 🐶 멍메이트(DogMate) 엣지 하드웨어 설정
# ==========================================

# 1. 클라우드 백엔드 연동 설정
# Cloud Run 배포 주소 (기본값) 또는 로컬 서버 주소
CLOUD_RUN_URL = "https://dogmate-backend-1089229092493.us-central1.run.app"
API_BASE_URL = os.getenv("API_BASE_URL", CLOUD_RUN_URL)
DEVICE_ID = os.getenv("DEVICE_ID", "dogmate-rpi3b-01")

# 2. 통신 주기 설정
TELEMETRY_INTERVAL_SEC = int(os.getenv("TELEMETRY_INTERVAL_SEC", "30"))  # 센서 주기 보고 (30초)
COMMAND_POLL_INTERVAL_SEC = int(os.getenv("COMMAND_POLL_INTERVAL_SEC", "3"))  # 원격 명령 폴링 (3초)

# 3. GrovePi+ 핀 번호 매핑
PIN_SOUND_SENSOR = 0       # A0: 사운드 센서 (아날로그 소음 감지)
PIN_LIGHT_SENSOR = 1       # A1: 조도 센서 (아날로그 밝기 감지)
PIN_DHT_SENSOR = 3         # D3: 온습도 센서 (DHT11/DHT22 디지털)
PIN_ULTRASONIC_SENSOR = 4  # D4: 초음파 거리 센서 (디지털 거리 측정)
PIN_SERVO_MOTOR = 5        # D5: SG-90 간식 투출 서보모터 (PWM 제어)
PIN_BUZZER = 6             # D6: 부저
PIN_LED = 7                # D7: 상태 표시 LED

# 4. 간식통(초음파) 보정 설정 (단위: cm)
# 간식이 가득 찼을 때 거리(최소)와 완전히 비었을 때 거리(최대)
TREAT_CONTAINER_EMPTY_CM = 20.0
TREAT_CONTAINER_FULL_CM = 4.0

# 5. 이상 짖음 감지 임계값
SOUND_ALERT_THRESHOLD = 70       # Grove 사운드센서 70dB 초과 시 AI 추론 트리거
BARK_CONFIDENCE_THRESHOLD = 0.35 # YAMNet 짖음 신뢰도 임계값

# 6. 야간 안심 조명 (조도 센서 연동)
NIGHT_LIGHT_THRESHOLD_LUX = 150  # 150 Lux 이하 시 야간 안심 LED 자동 점등

# 7. 현관문 배회(ROI) 감지 임계값 (Ogata 2016 논문 기반)
DOORWAY_STAY_THRESHOLD_SEC = 5.0 # 현관 구역 5초 이상 지속 체류 시 분리불안 배회 경보 트리거

