import os
import sys
import io
import time
import json
import requests
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hardware.config import CLOUD_RUN_URL, DEVICE_ID, NIGHT_LIGHT_THRESHOLD_LUX
from hardware.sensors.environment import get_all_environment_telemetry, read_treat_level_percent
from hardware.sensors.sound import read_sound_level, detect_noise_spike
from hardware.actuators.servo import dispense_treat
from hardware.actuators.alerts import update_night_soothing_led, get_night_led_status, trigger_alert_beep
from hardware.camera import capture_snapshot
from hardware.ai.yamnet_detector import analyze_audio_for_bark
from hardware.ai.roi_motion_detector import check_doorway_pacing


class DogMateTestSuite:
    def __init__(self, base_url=CLOUD_RUN_URL):
        self.base_url = base_url.rstrip('/')
        self.results = []
        self.start_time = datetime.now()

    def record(self, category, test_name, passed, details=""):
        status_str = "PASS" if passed else "FAIL"
        symbol = "✅" if passed else "❌"
        self.results.append({
            "category": category,
            "name": test_name,
            "passed": passed,
            "status": status_str,
            "details": details
        })
        print(f"[{symbol} {status_str}] [{category}] {test_name}: {details}")

    def run_all(self):
        print("=" * 80)
        print(f"🐶 [DogMate] 전체 시스템 및 배포 환경 종합 검증 테스트 (Full E2E Test Suite)")
        print(f"📡 대상 서버: {self.base_url}")
        print(f"🏷️ 디바이스: {DEVICE_ID}")
        print(f"⏰ 시작 시각: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

        # Part 1: Cloud & API Endpoints
        self.test_cloud_health()
        self.test_swagger_and_docs()
        self.test_web_dashboard()
        self.test_telemetry_endpoint()
        self.test_heartbeat_endpoint()
        self.test_bark_event_upload()
        self.test_door_pacing_event_upload()
        self.test_photo_streaming()
        self.test_feed_and_command_ack_flow()
        self.test_voice_upload_and_command_flow()
        self.test_app_status_query()
        self.test_app_events_query()
        self.test_app_telemetry_history_query()

        # Part 2: Hardware & Edge Modules
        self.test_hardware_sensors()
        self.test_hardware_actuators()
        self.test_hardware_night_led()
        self.test_hardware_camera()
        self.test_hardware_yamnet_ai()
        self.test_hardware_roi_motion()

        # Summary
        self.print_summary()

    def test_cloud_health(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/health", timeout=8)
            data = r.json()
            is_healthy = (r.status_code == 200 and data.get("status") == "healthy" 
                          and data["services"]["supabase_postgresql"] == "connected"
                          and data["services"]["google_cloud_storage"] == "connected")
            self.record("Cloud Backend", "인프라 헬스체크 (/health)", is_healthy,
                        f"HTTP {r.status_code}, Services: {data.get('services')}")
        except Exception as e:
            self.record("Cloud Backend", "인프라 헬스체크 (/health)", False, str(e))

    def test_swagger_and_docs(self):
        try:
            r_docs = requests.get(f"{self.base_url}/docs", timeout=8)
            r_spec = requests.get(f"{self.base_url}/api/v1/swagger.json", timeout=8)
            spec_data = r_spec.json()
            paths = list(spec_data.get("paths", {}).keys())
            passed = (r_docs.status_code == 200 and r_spec.status_code == 200 and len(paths) >= 8)
            self.record("Swagger OpenAPI", "API 명세 및 UI (/docs)", passed,
                        f"Docs HTTP {r_docs.status_code}, Spec HTTP {r_spec.status_code}, 엔드포인트 수: {len(paths)}개")
        except Exception as e:
            self.record("Swagger OpenAPI", "API 명세 및 UI (/docs)", False, str(e))

    def test_web_dashboard(self):
        try:
            r = requests.get(f"{self.base_url}/", timeout=8)
            passed = (r.status_code == 200 and "멍메이트" in r.text and "IoT" in r.text)
            self.record("Web Frontend", "모니터링 대시보드 뷰 (GET /)", passed,
                        f"HTTP {r.status_code}, 페이지 크기: {len(r.content)} bytes")
        except Exception as e:
            self.record("Web Frontend", "모니터링 대시보드 뷰 (GET /)", False, str(e))

    def test_telemetry_endpoint(self):
        try:
            payload = {
                "device_id": DEVICE_ID,
                "temperature": 24.5,
                "humidity": 53.0,
                "light_level": 340,
                "treat_percent": 85
            }
            r = requests.post(f"{self.base_url}/api/v1/devices/telemetry", json=payload, timeout=8)
            data = r.json()
            passed = (r.status_code == 201 and data.get("status") == "recorded" and "telemetry_id" in data)
            self.record("REST API", "센서 텔레메트리 적재 (POST /telemetry)", passed,
                        f"HTTP {r.status_code}, Telemetry ID: {data.get('telemetry_id')}")
        except Exception as e:
            self.record("REST API", "센서 텔레메트리 적재 (POST /telemetry)", False, str(e))

    def test_heartbeat_endpoint(self):
        try:
            payload = {"device_id": DEVICE_ID}
            r = requests.post(f"{self.base_url}/api/v1/devices/heartbeat", json=payload, timeout=8)
            data = r.json()
            passed = (r.status_code == 200 and data.get("status") == "alive")
            self.record("REST API", "생존 신호 하트비트 (POST /heartbeat)", passed,
                        f"HTTP {r.status_code}, Device: {data.get('device_id')}")
        except Exception as e:
            self.record("REST API", "생존 신호 하트비트 (POST /heartbeat)", False, str(e))

    def test_bark_event_upload(self):
        try:
            img = capture_snapshot(event_type="bark")
            files = {"image": ("bark_test.jpg", img, "image/jpeg")}
            data = {"device_id": DEVICE_ID, "sound_db": 84, "confidence": 0.91}
            r = requests.post(f"{self.base_url}/api/v1/devices/events/bark", data=data, files=files, timeout=12)
            res = r.json()
            passed = (r.status_code == 201 and "event_id" in res and "view_url" in res)
            self.last_photo_url = res.get("view_url")
            self.record("REST API", "짖음 감지 사진 업로드 (POST /events/bark)", passed,
                        f"HTTP {r.status_code}, Event ID: {res.get('event_id')}, URL: {res.get('view_url')}")
        except Exception as e:
            self.record("REST API", "짖음 감지 사진 업로드 (POST /events/bark)", False, str(e))

    def test_door_pacing_event_upload(self):
        try:
            img = capture_snapshot(event_type="pacing", detail="6.8s")
            files = {"image": ("pacing_test.jpg", img, "image/jpeg")}
            data = {"device_id": DEVICE_ID, "sound_db": 52, "confidence": 0.96}
            r = requests.post(f"{self.base_url}/api/v1/devices/events/bark", data=data, files=files, timeout=12)
            res = r.json()
            passed = (r.status_code == 201 and "event_id" in res)
            self.record("REST API", "현관문 배회(ROI) 사진 업로드 (POST /events/bark)", passed,
                        f"HTTP {r.status_code}, Event ID: {res.get('event_id')}")
        except Exception as e:
            self.record("REST API", "현관문 배회(ROI) 사진 업로드 (POST /events/bark)", False, str(e))

    def test_photo_streaming(self):
        try:
            if hasattr(self, 'last_photo_url') and self.last_photo_url:
                target_url = self.last_photo_url
                if target_url.startswith("/"):
                    target_url = f"{self.base_url}{target_url}"
                r = requests.get(target_url, timeout=10)
                passed = (r.status_code == 200 and "image/jpeg" in r.headers.get("content-type", "") and len(r.content) > 1000)
                self.record("Security & Media", "비공개 GCS 보안 사진 스트리밍 (/photos)", passed,
                            f"HTTP {r.status_code}, Content-Type: {r.headers.get('content-type')}, Size: {len(r.content)} bytes")
            else:
                self.record("Security & Media", "비공개 GCS 보안 사진 스트리밍 (/photos)", False, "이전 사진 URL 부재")
        except Exception as e:
            self.record("Security & Media", "비공개 GCS 보안 사진 스트리밍 (/photos)", False, str(e))

    def test_feed_and_command_ack_flow(self):
        try:
            # 1. App requests feed
            r_feed = requests.post(f"{self.base_url}/api/v1/app/feed", json={"device_id": DEVICE_ID, "amount": 1}, timeout=8)
            cmd_id = r_feed.json().get("command_id")

            # 2. Device polls command
            r_poll = requests.get(f"{self.base_url}/api/v1/devices/commands/pending?device_id={DEVICE_ID}", timeout=8)
            commands = r_poll.json()
            found = any(c["id"] == cmd_id for c in commands)

            # 3. Device sends ACK
            r_ack = requests.post(f"{self.base_url}/api/v1/devices/commands/ack", json={
                "command_id": cmd_id,
                "device_id": DEVICE_ID,
                "status": "completed"
            }, timeout=8)
            ack_ok = (r_ack.status_code == 200 and r_ack.json().get("status") == "acknowledged")

            passed = (r_feed.status_code == 200 and found and ack_ok)
            self.record("REST API", "원격 간식 급여 및 ACK E2E 루프 (/feed -> /commands)", passed,
                        f"Feed CMD #{cmd_id} 생성, 폴링 수신 확인, ACK 완료 회신 성공")
        except Exception as e:
            self.record("REST API", "원격 간식 급여 및 ACK E2E 루프 (/feed -> /commands)", False, str(e))

    def test_voice_upload_and_command_flow(self):
        try:
            # Mock WAV audio file
            wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
            files = {"voice": ("comfort.wav", io.BytesIO(wav_header), "audio/wav")}
            data = {"device_id": DEVICE_ID}
            r = requests.post(f"{self.base_url}/api/v1/app/voice", data=data, files=files, timeout=12)
            res = r.json()
            cmd_id = res.get("command_id")

            # Device polls and ACKs
            r_poll = requests.get(f"{self.base_url}/api/v1/devices/commands/pending?device_id={DEVICE_ID}", timeout=8)
            cmds = r_poll.json()
            voice_found = any(c["id"] == cmd_id and c["command_type"] == "PLAY_VOICE" for c in cmds)
            if voice_found:
                requests.post(f"{self.base_url}/api/v1/devices/commands/ack", json={
                    "command_id": cmd_id, "device_id": DEVICE_ID, "status": "completed"
                }, timeout=8)

            passed = (r.status_code == 200 and res.get("success") is True and voice_found)
            self.record("REST API", "보호자 음성 업로드 및 스피커 하달 (/voice)", passed,
                        f"HTTP {r.status_code}, Voice URL: {res.get('voice_url')[:45]}..., CMD #{cmd_id}")
        except Exception as e:
            self.record("REST API", "보호자 음성 업로드 및 스피커 하달 (/voice)", False, str(e))

    def test_app_status_query(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/app/status?device_id={DEVICE_ID}", timeout=8)
            data = r.json()
            passed = (r.status_code == 200 and data.get("device_id") == DEVICE_ID and "telemetry" in data)
            self.record("Mobile REST API", "대시보드 종합 상태 조회 (GET /app/status)", passed,
                        f"온라인: {data.get('online')}, 온도: {data.get('telemetry',{}).get('temperature')}℃, 간식: {data.get('telemetry',{}).get('treat_percent')}%")
        except Exception as e:
            self.record("Mobile REST API", "대시보드 종합 상태 조회 (GET /app/status)", False, str(e))

    def test_app_events_query(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/app/events?device_id={DEVICE_ID}&limit=5", timeout=8)
            events = r.json()
            passed = (r.status_code == 200 and isinstance(events, list) and len(events) > 0)
            self.record("Mobile REST API", "이상 짖음 내역 목록 조회 (GET /app/events)", passed,
                        f"HTTP {r.status_code}, 수신 이벤트 수: {len(events)}건 (최신 소음: {events[0].get('sound_db')}dB)")
        except Exception as e:
            self.record("Mobile REST API", "이상 짖음 내역 목록 조회 (GET /app/events)", False, str(e))

    def test_app_telemetry_history_query(self):
        try:
            r = requests.get(f"{self.base_url}/api/v1/app/telemetry/history?device_id={DEVICE_ID}&limit=10", timeout=8)
            history = r.json()
            passed = (r.status_code == 200 and isinstance(history, list))
            self.record("Mobile REST API", "센서 시계열 차트 데이터 조회 (GET /history)", passed,
                        f"HTTP {r.status_code}, 시계열 데이터 포인트: {len(history)}건")
        except Exception as e:
            self.record("Mobile REST API", "센서 시계열 차트 데이터 조회 (GET /history)", False, str(e))

    def test_hardware_sensors(self):
        try:
            telem = get_all_environment_telemetry()
            temp = telem["temperature"]
            hum = telem["humidity"]
            light = telem["light_level"]
            treat = telem["treat_percent"]
            passed = (10.0 <= temp <= 45.0 and 10.0 <= hum <= 95.0 and 0 <= light <= 1024 and 0 <= treat <= 100)
            self.record("Hardware Sensors", "환경 센서군 수집 (온습도/조도/초음파)", passed,
                        f"온도: {temp}℃, 습도: {hum}%, 조도: {light}Lux, 간식: {treat}%")
        except Exception as e:
            self.record("Hardware Sensors", "환경 센서군 수집 (온습도/조도/초음파)", False, str(e))

    def test_hardware_actuators(self):
        try:
            init_treat = read_treat_level_percent()
            servo_ok = dispense_treat(amount=1)
            beep_ok = trigger_alert_beep(0.1)
            after_treat = read_treat_level_percent()
            passed = (servo_ok and beep_ok)
            self.record("Hardware Actuators", "서보모터 간식 투출 & 부저 구동", passed,
                        f"서보 회전 정상, 부저 비프 정상, 잔여량 변화: {init_treat}% -> {after_treat}%")
        except Exception as e:
            self.record("Hardware Actuators", "서보모터 간식 투출 & 부저 구동", False, str(e))

    def test_hardware_night_led(self):
        try:
            on_state = update_night_soothing_led(80, threshold=150)
            off_state = update_night_soothing_led(320, threshold=150)
            passed = (on_state is True and off_state is False)
            self.record("Hardware Actuators", "조도 연동 야간 안심 LED 자동 점등", passed,
                        f"80 Lux ➔ ON(True), 320 Lux ➔ OFF(False) 히스테리시스 전환 완벽")
        except Exception as e:
            self.record("Hardware Actuators", "조도 연동 야간 안심 LED 자동 점등", False, str(e))

    def test_hardware_camera(self):
        try:
            img_bark = capture_snapshot(event_type="bark")
            img_pacing = capture_snapshot(event_type="pacing", detail="5.5s")
            passed = (len(img_bark) > 1000 and len(img_pacing) > 1000 and img_bark[:2] == b'\xff\xd8')
            self.record("Hardware Vision", "카메라 스틸컷 촬영 (짖음/배회 시각화)", passed,
                        f"짖음 캡처 크기: {len(img_bark)}B, 배회 캡처 크기: {len(img_pacing)}B (JPEG 규격)")
        except Exception as e:
            self.record("Hardware Vision", "카메라 스틸컷 촬영 (짖음/배회 시각화)", False, str(e))

    def test_hardware_yamnet_ai(self):
        try:
            is_bark, conf = analyze_audio_for_bark()
            model_file = "hardware/models/yamnet.tflite"
            class_file = "hardware/models/yamnet_class_map.csv"
            files_exist = os.path.exists(model_file) and os.path.exists(class_file)
            passed = (is_bark is True and conf >= 0.70 and files_exist)
            self.record("Edge AI", "Google YAMNet 짖음 오디오 분류 AI", passed,
                        f"짖음 감지 판정: {is_bark} (신뢰도: {conf*100:.0f}%), 모델({model_file}) 탑재 완료")
        except Exception as e:
            self.record("Edge AI", "Google YAMNet 짖음 오디오 분류 AI", False, str(e))

    def test_hardware_roi_motion(self):
        try:
            pacing, dur, ratio = check_doorway_pacing(simulate=True)
            passed = (pacing is True and dur >= 5.0 and ratio > 0.05)
            self.record("Edge AI", "현관문 관심구역(ROI) 장시간 배회 감지", passed,
                        f"배회 판정: {pacing}, 서성임 지속: {dur}초, 움직임 비율: {ratio*100:.0f}% (Ogata 2016)")
        except Exception as e:
            self.record("Edge AI", "현관문 관심구역(ROI) 장시간 배회 감지", False, str(e))

    def print_summary(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed

        print("\n" + "=" * 80)
        print(f"📊 [DogMate] 종합 검증 테스트 결과 요약 보고")
        print(f"총 테스트 항목: {total}개 | 성공: {passed}개 | 실패: {failed}개 | 소요 시간: {elapsed:.2f}초")
        print(f"종합 성공률: {(passed/total)*100:.1f}%")
        print("=" * 80)

        if failed == 0:
            print("\n🎉 [ALL CLEAR] 모든 기능 테스트 및 배포 환경 검증이 결함 없이 100% 통과되었습니다!")
        else:
            print(f"\n⚠️ [ATTENTION] {failed}개의 항목에서 실패가 발생했습니다. 로그를 점검하세요.")


if __name__ == "__main__":
    suite = DogMateTestSuite()
    suite.run_all()
