import os
import sys
import time
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hardware.config import CLOUD_RUN_URL, DEVICE_ID
from hardware.client import DogMateEdgeClient
from hardware.actuators.servo import dispense_treat


def run_interactive_simulator():
    print("=" * 65)
    print("🐶 멍메이트(DogMate) 엣지 하드웨어 통합 시뮬레이터 콘솔")
    print(f"📡 연결 대상: Google Cloud Run ({CLOUD_RUN_URL})")
    print(f"🏷️ 디바이스 ID: {DEVICE_ID}")
    print("=" * 65)

    client = DogMateEdgeClient(api_url=CLOUD_RUN_URL)

    while True:
        print("\n[테스트 메뉴를 선택하세요]")
        print("  1. 📊 실내 온습도/조도/간식 텔레메트리 1회 전송")
        print("  2. 🚨 이상 짖음 감지 시뮬레이션 (카메라 캡처 ➔ GCS 업로드 ➔ FCM 푸시)")
        print("  3. 🍖 SG-90 간식 투출 서보모터 단독 구동 테스트")
        print("  4. 📥 클라우드 원격 명령 큐 폴링 및 실행 (ACK 완료 보고)")
        print("  5. 🚀 엣지 클라이언트 백그라운드 자동 루프 가동 (정기 보고 + 상시 감시)")
        print("  0. 🛑 시뮬레이터 종료")
        
        try:
            choice = input("\n👉 선택 (0~5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n시뮬레이터를 종료합니다.")
            break

        if choice == "1":
            print("\n📊 텔레메트리 데이터 수집 및 클라우드 전송 중...")
            client.send_telemetry()
        elif choice == "2":
            sound = 85
            conf = 0.94
            print(f"\n🚨 [시뮬레이션] 짖음 소음 {sound}dB 발생! (AI 신뢰도 {int(conf*100)}%)")
            client.report_bark_event(sound_db=sound, confidence=conf)
        elif choice == "3":
            print("\n🍖 간식 서보모터 구동 테스트 중...")
            dispense_treat(amount=1)
        elif choice == "4":
            print("\n📥 클라우드 대기열 명령 확인 중...")
            client.poll_commands()
        elif choice == "5":
            print("\n🚀 엣지 클라이언트 연속 데몬을 시작합니다. (중단: Ctrl+C)")
            try:
                client.start()
            except KeyboardInterrupt:
                print("\n자동 루프가 중지되었습니다.")
        elif choice == "0":
            print("\n시뮬레이터를 종료합니다.")
            break
        else:
            print("⚠️ 잘못된 입력입니다. 0부터 5까지 숫자를 입력해주세요.")


if __name__ == "__main__":
    run_interactive_simulator()
