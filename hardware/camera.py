import io
import time
from datetime import datetime

# 라즈베리파이 CSI 카메라 지원 확인
try:
    from picamera2 import Picamera2
    PICAM2_AVAILABLE = True
except ImportError:
    PICAM2_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# 시뮬레이션용 Pillow 라이브러리
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def capture_snapshot(event_type="bark", detail="") -> bytes:
    """
    카메라로 현장 사진을 캡처하여 JPEG 바이트 스트림으로 반환합니다.
    (1순위: PiCamera2 CSI, 2순위: OpenCV USB 웹캠, 3순위: 고품질 시뮬레이션 이미지 생성)
    """
    # 1. Raspberry Pi CSI Camera (Picamera2)
    if PICAM2_AVAILABLE:
        try:
            picam = Picamera2()
            config = picam.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
            picam.configure(config)
            picam.start()
            time.sleep(0.5)  # 센서 자동 노출 대기
            stream = io.BytesIO()
            picam.capture_file(stream, format="jpeg")
            picam.stop()
            picam.close()
            return stream.getvalue()
        except Exception as e:
            print(f"[Camera Warning] PiCamera2 캡처 실패, 폴백 시도: {e}")

    # 2. USB WebCam via OpenCV
    if OPENCV_AVAILABLE:
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    _, buffer = cv2.imencode('.jpg', frame)
                    return buffer.tobytes()
        except Exception as e:
            print(f"[Camera Warning] OpenCV 웹캠 캡처 실패: {e}")

    # 3. 가상 시뮬레이션 카메라 (맥북 / 개발 환경)
    return generate_simulated_pet_image(event_type=event_type, detail=detail)


def generate_simulated_pet_image(event_type="bark", detail="") -> bytes:
    """
    실제 카메라가 없는 환경에서도 대시보드와 GCS에 실제처럼 표시될 수 있도록
    반려견 모니터링 시뮬레이션 JPEG 이미지를 생성합니다.
    (이상 짖음 또는 현관문 배회 ROI 상황에 맞는 시각화 제공)
    """
    width, height = 640, 480
    if not PIL_AVAILABLE:
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'

    img = Image.new('RGB', (width, height), color=(240, 235, 225))
    draw = ImageDraw.Draw(img)

    # 거실 바닥과 벽 구분선
    draw.rectangle([(0, 320), (width, height)], fill=(210, 180, 140))  # 원목 바닥
    draw.rectangle([(0, 0), (width, 320)], fill=(245, 245, 240))      # 벽면

    if event_type == "pacing":
        # 현관문(Doorway) 및 ROI 경계 상자 시각화
        draw.rectangle([(50, 100), (220, 420)], fill=(200, 195, 190), outline=(130, 120, 110), width=3) # 현관문
        draw.ellipse([(200, 260), (210, 270)], fill=(80, 70, 60)) # 문 손잡이
        # 현관문 ROI 감지 구역 (붉은색 점선 박스 효과)
        draw.rectangle([(40, 90), (230, 430)], outline=(231, 76, 60), width=3)
        draw.text((45, 70), "🚨 [ROI ALERT] Doorway Area", fill=(231, 76, 60))

        # 현관 앞에 서성이는 강아지 (좌측 배치)
        draw.ellipse([(140, 290), (240, 370)], fill=(218, 165, 32)) # 몸통
        draw.ellipse([(120, 240), (180, 300)], fill=(218, 165, 32)) # 머리
        draw.polygon([(120, 250), (105, 280), (130, 270)], fill=(160, 82, 45))
        draw.polygon([(160, 250), (175, 280), (150, 270)], fill=(160, 82, 45))
        draw.ellipse([(130, 260), (138, 268)], fill=(20, 20, 20))
        draw.ellipse([(150, 260), (158, 268)], fill=(20, 20, 20))

        alert_title = f"Alert: Doorway Pacing Detected ({detail or 'Ogata 2016'})"
    else:
        # 일반 방석 및 짖음 포즈 (중앙 배치)
        draw.ellipse([(180, 280), (460, 380)], fill=(130, 160, 200), outline=(100, 130, 170), width=3)
        draw.ellipse([(250, 240), (390, 340)], fill=(218, 165, 32))
        draw.ellipse([(280, 180), (360, 260)], fill=(218, 165, 32))
        draw.polygon([(280, 190), (260, 230), (285, 220)], fill=(160, 82, 45))
        draw.polygon([(360, 190), (380, 230), (355, 220)], fill=(160, 82, 45))
        draw.ellipse([(300, 205), (310, 215)], fill=(20, 20, 20))
        draw.ellipse([(330, 205), (340, 215)], fill=(20, 20, 20))
        draw.ellipse([(315, 218), (325, 228)], fill=(20, 20, 20))

        # 짖음 말풍선
        draw.rectangle([(380, 140), (520, 190)], fill=(255, 255, 255), outline=(231, 76, 60), width=2)
        draw.polygon([(380, 175), (360, 190), (385, 185)], fill=(255, 255, 255))
        draw.text((400, 155), "멍! 멍! (Bark!)", fill=(231, 76, 60))
        alert_title = "Alert: Bark Detected (YAMNet AI)"

    # 상단 타임스탬프 및 메타데이터 배너
    draw.rectangle([(0, 0), (width, 36)], fill=(44, 62, 80))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((15, 10), f"🐶 DogMate Live Camera | {now_str} | {alert_title}", fill=(255, 255, 255))

    # 하단 캡션
    draw.text((15, height - 25), "[DogMate RPi 3B Edge AI] Separation Anxiety Monitor", fill=(100, 100, 100))

    stream = io.BytesIO()
    img.save(stream, format="JPEG", quality=85)
    return stream.getvalue()

