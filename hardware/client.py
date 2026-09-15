import os
import sys
import time
import argparse
import threading
import requests
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hardware.config import (
    API_BASE_URL,
    DEVICE_ID,
    TELEMETRY_INTERVAL_SEC,
    COMMAND_POLL_INTERVAL_SEC,
    SOUND_ALERT_THRESHOLD,
    CLOUD_RUN_URL,
    NIGHT_LIGHT_THRESHOLD_LUX,
    DOORWAY_STAY_THRESHOLD_SEC
)
from hardware.sensors.environment import get_all_environment_telemetry
from hardware.sensors.sound import detect_noise_spike
from hardware.actuators.servo import dispense_treat
from hardware.actuators.speaker import play_audio_file
from hardware.actuators.alerts import trigger_alert_beep, set_status_led, update_night_soothing_led, get_night_led_status
from hardware.camera import capture_snapshot
from hardware.ai.yamnet_detector import analyze_audio_for_bark
from hardware.ai.roi_motion_detector import check_doorway_pacing


class DogMateEdgeClient:
    """
    라즈베리파이 3B 멍메이트(DogMate) 엣지 통합 클라이언트 데몬
    - 3-Tier 엔터프라이즈 아키텍처 연동
    - 센서 텔레메트리 적재, YAMNet 이상 짖음 긴급 리포트, 원격 명령 실시간 수행
    """
    def __init__(self, api_url=API_BASE_URL, device_id=DEVICE_ID):
        self.api_url = api_url.rstrip('/')
        self.device_id = device_id
        self.running = False
        self.last_bark_report_time = 0
        self.bark_cooldown_sec = 10  # 연속 짖음 시 푸시 도배 방지 쿨다운 (10초)

    def print_banner(self):
        print("=" * 65)
        print("🐶 [DogMate] 라즈베리파이 3B 엣지 클라이언트 데몬 가동")
        print(f"📡 연동 클라우드: {self.api_url}")
        print(f"🏷️ 디바이스 ID: {self.device_id}")
        print(f"⏱️ 텔레메트리 주기: {TELEMETRY_INTERVAL_SEC}초 | 명령 폴링: {COMMAND_POLL_INTERVAL_SEC}초")
        print("=" * 65)

    # ==========================================
    # 1. 텔레메트리 보고
    # ==========================================
    def send_telemetry(self):
        """환경 센서 수집 및 클라우드 적재"""
        data = get_all_environment_telemetry()
        payload = {
            "device_id": self.device_id,
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "light_level": data["light_level"],
            "treat_percent": data["treat_percent"]
        }
        # 조도 센서 기반 야간 안심 조명 자동 제어
        is_night = update_night_soothing_led(data["light_level"], threshold=NIGHT_LIGHT_THRESHOLD_LUX)
        night_str = " | 💡 [야간LED 켜짐]" if is_night else ""

        url = f"{self.api_url}/api/v1/devices/telemetry"
        try:
            res = requests.post(url, json=payload, timeout=6)
            if res.status_code in [200, 201]:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 [Telemetry] 🌡️ {data['temperature']}℃ | 💧 {data['humidity']}% | ☀️ {data['light_level']}Lux | 🍖 {data['treat_percent']}%{night_str} 전송 완료")
                return True
            else:
                print(f"⚠️ [Telemetry Warning] 응답 코드 {res.status_code}: {res.text}")
        except Exception as e:
            print(f"❌ [Telemetry Error] 클라우드 전송 실패: {e}")
        return False

    # ==========================================
    # 2. 이상행동 이벤트 리포트 (짖음 & 현관문 배회)
    # ==========================================
    def report_doorway_pacing_event(self, duration_sec=6.5, motion_ratio=0.25):
        """현관문 관심 구역(ROI) 장시간 서성임(배회 행동) 감지 시 사진 캡처 및 클라우드 업로드"""
        now = time.time()
        if now - self.last_bark_report_time < self.bark_cooldown_sec:
            return  # 쿨다운 중
        self.last_bark_report_time = now

        print(f"\n🚪 [{datetime.now().strftime('%H:%M:%S')}] [ALERT] 현관문 장시간 서성임(배회) 감지! (지속: {duration_sec}초, 모션비율: {int(motion_ratio*100)}%)")
        set_status_led(True)
        trigger_alert_beep(0.2)

        # 현관문 배회 전용 시각화 스냅샷 캡처
        image_bytes = capture_snapshot(event_type="pacing", detail=f"{duration_sec}s")

        url = f"{self.api_url}/api/v1/devices/events/bark"
        files = {'image': ('door_pacing.jpg', image_bytes, 'image/jpeg')}
        data = {
            'device_id': self.device_id,
            'sound_db': 55, # 생활 소음 상태이나 비전 배회 감지
            'confidence': 0.95
        }
        try:
            print("☁️ [Cloud] 현관문 배회 이상행동 이벤트 및 캡처 사진 업로드 중...")
            res = requests.post(url, data=data, files=files, timeout=12)
            if res.status_code in [200, 201]:
                resp_json = res.json()
                print(f"✅ [Cloud] 현관문 배회 이벤트 리포트 완료! (Event ID: {resp_json.get('event_id')})")
                print(f"🔗 [Cloud GCS Photo]: {resp_json.get('view_url')}")
            else:
                print(f"❌ [Cloud Error] 업로드 응답 실패: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ [Cloud Error] 배회 이벤트 전송 실패: {e}")
        finally:
            set_status_led(False)

    def report_bark_event(self, sound_db=78, confidence=0.89):
        """이상 짖음 감지 시 현장 사진 캡처 후 클라우드로 긴급 업로드"""
        now = time.time()
        if now - self.last_bark_report_time < self.bark_cooldown_sec:
            return  # 쿨다운 중
        self.last_bark_report_time = now

        print(f"\n🚨 [{datetime.now().strftime('%H:%M:%S')}] [ALERT] 이상 짖음 감지! (소음: {sound_db}dB, AI신뢰도: {int(confidence*100)}%)")
        set_status_led(True)
        trigger_alert_beep(0.3)

        # 1. 카메라 캡처
        print("📷 [Camera] 현장 상황 사진 캡처 중...")
        image_bytes = capture_snapshot()

        # 2. 클라우드 멀티파트 업로드
        url = f"{self.api_url}/api/v1/devices/events/bark"
        files = {
            'image': ('capture.jpg', image_bytes, 'image/jpeg')
        }
        data = {
            'device_id': self.device_id,
            'sound_db': sound_db,
            'confidence': confidence
        }

        try:
            print("☁️ [Cloud] GCS 및 Supabase로 이벤트 및 사진 업로드 중...")
            res = requests.post(url, data=data, files=files, timeout=12)
            if res.status_code in [200, 201]:
                resp_json = res.json()
                print(f"✅ [Cloud] 짖음 이벤트 리포트 완료! (Event ID: {resp_json.get('event_id')})")
                print(f"🔗 [Cloud GCS Photo]: {resp_json.get('view_url')}")
            else:
                print(f"❌ [Cloud Error] 업로드 응답 실패: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ [Cloud Error] 짖음 이벤트 전송 실패: {e}")
        finally:
            set_status_led(False)

    # ==========================================
    # 3. 원격 명령 폴링 및 실행
    # ==========================================
    def poll_commands(self):
        """클라우드에 대기 중인 원격 제어 명령(간식 급여, 음성 재생) 조회 및 실행"""
        url = f"{self.api_url}/api/v1/devices/commands/pending?device_id={self.device_id}"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                commands = res.json()
                for cmd in commands:
                    self.execute_command(cmd)
        except Exception as e:
            # 네트워크 순시 장애 시 에러 로그 최소화
            pass

    def execute_command(self, cmd):
        """수신된 명령 타입별 액추에이터 실행 및 ACK 회신"""
        cmd_id = cmd["id"]
        cmd_type = cmd["command_type"]
        payload = cmd.get("payload", {})
        print(f"\n📩 [Command Received] 명령 수신 [#{cmd_id}]: {cmd_type} (내용: {payload})")

        success = False
        if cmd_type == "FEED_TREAT":
            amount = payload.get("amount", 1) if isinstance(payload, dict) else 1
            success = dispense_treat(amount)
            trigger_alert_beep(0.2)
            # 간식 투출 후 즉시 텔레메트리 갱신 전송
            self.send_telemetry()

        elif cmd_type == "PLAY_VOICE":
            voice_url = payload.get("voice_url") if isinstance(payload, dict) else None
            if voice_url:
                success = play_audio_file(voice_url)
            else:
                print("❌ [Command Error] 음성 URL이 없습니다.")

        # ACK 완료 보고
        self.send_command_ack(cmd_id, "completed" if success else "failed")

    def send_command_ack(self, cmd_id, status="completed"):
        """명령 실행 결과 클라우드 보고"""
        url = f"{self.api_url}/api/v1/devices/commands/ack"
        try:
            requests.post(url, json={
                "command_id": cmd_id,
                "device_id": self.device_id,
                "status": status
            }, timeout=5)
            print(f"✅ [Command ACK] 명령 [#{cmd_id}] 완료 보고 전송 ({status})")
        except Exception as e:
            print(f"❌ [Command ACK Error] {e}")

    # ==========================================
    # 4. 백그라운드 스레드 루프
    # ==========================================
    def _telemetry_loop(self):
        while self.running:
            self.send_telemetry()
            time.sleep(TELEMETRY_INTERVAL_SEC)

    def _command_loop(self):
        while self.running:
            self.poll_commands()
            time.sleep(COMMAND_POLL_INTERVAL_SEC)

    def _sound_monitoring_loop(self):
        """사운드 센서 임계값 감시 및 YAMNet AI 추론 루프"""
        while self.running:
            is_loud, sound_db = detect_noise_spike(threshold_db=SOUND_ALERT_THRESHOLD)
            if is_loud:
                # 소음 급증 시 YAMNet AI 분석
                is_bark, confidence = analyze_audio_for_bark()
                if is_bark:
                    self.report_bark_event(sound_db=sound_db, confidence=confidence)
            time.sleep(0.5)

    def start(self):
        """엣지 데몬 시작"""
        self.running = True
        self.print_banner()

        # 시작 즉시 1회 텔레메트리 발송 (디바이스 등록 및 온라인 확인)
        self.send_telemetry()

        # 백그라운드 작업자 스레드 시작
        t_telem = threading.Thread(target=self._telemetry_loop, daemon=True)
        t_cmd = threading.Thread(target=self._command_loop, daemon=True)
        t_sound = threading.Thread(target=self._sound_monitoring_loop, daemon=True)

        t_telem.start()
        t_cmd.start()
        t_sound.start()

        print("\n🚀 [System Ready] 모든 센서 및 원격 제어 감시 루프가 정상 동작 중입니다.")
        print("💡 (Ctrl+C를 누르면 안전하게 종료됩니다.)\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 [System Stopping] 클라이언트 데몬을 종료합니다...")
            self.running = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="멍메이트(DogMate) 라즈베리파이 엣지 클라이언트")
    parser.add_argument("--url", type=str, default=API_BASE_URL, help="클라우드 백엔드 API URL")
    parser.add_argument("--cloud", action="store_true", help="배포된 Google Cloud Run 주소 강제 적용")
    parser.add_argument("--local", action="store_true", help="로컬 서버(http://localhost:5001) 적용")
    parser.add_argument("--test-bark", action="store_true", help="이상 짖음 감지 및 사진 업로드 즉시 테스트")
    parser.add_argument("--test-feed", action="store_true", help="간식 서보모터 투출 즉시 테스트")
    parser.add_argument("--test-pacing", action="store_true", help="현관문 배회(ROI) 감지 및 스냅샷 업로드 즉시 테스트")
    parser.add_argument("--test-night-led", action="store_true", help="조도 센서 연동 야간 안심 LED 자동 점등 테스트")
    
    args = parser.parse_args()

    target_url = args.url
    if args.cloud:
        target_url = CLOUD_RUN_URL
    elif args.local:
        target_url = "http://localhost:5001"

    client = DogMateEdgeClient(api_url=target_url)

    if args.test_bark:
        print("🧪 [Test Mode] 짖음 감지 + 카메라 캡처 + GCS/FCM 업로드 단독 테스트 실행")
        client.report_bark_event(sound_db=82, confidence=0.92)
    elif args.test_pacing:
        print("🧪 [Test Mode] 현관문 관심구역(ROI) 배회 행동 감지 단독 테스트 실행")
        client.report_doorway_pacing_event(duration_sec=7.2, motion_ratio=0.28)
    elif args.test_night_led:
        print("🧪 [Test Mode] 야간 안심 LED 제어 테스트 실행")
        print("1. 어두운 환경 시뮬레이션 (80 Lux):")
        update_night_soothing_led(80, threshold=150)
        time.sleep(1)
        print("2. 밝은 환경 시뮬레이션 (350 Lux):")
        update_night_soothing_led(350, threshold=150)
    elif args.test_feed:
        print("🧪 [Test Mode] 간식 서보모터 투출 단독 테스트 실행")
        dispense_treat(amount=1)
    else:
        client.start()
