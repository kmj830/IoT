# 🐶 멍메이트(DogMate) 시스템 구현 및 배포 E2E 종합 검증 보고서
> **과목**: 국립금오공과대학교 2026-2 IoT기초설계 (컴퓨터공학전공)  
> **팀원**: 김민중, 김영재  
> **검증 대상**: Google Cloud Run 프로덕션 서버, Supabase DB, Google Cloud Storage, 라즈베리파이 엣지 데몬  
> **검증 결과**: **19개 전 항목 100% 결함 제로 합격 (Pass: 19 / Fail: 0)**  
> **문서 버전**: v1.0 (최종 종합 검증 완료본)  
> **공식 PDF 문서**: [`docs/시스템_구현_및_배포_검증_보고서.pdf`](시스템_구현_및_배포_검증_보고서.pdf)

---

## 📌 1. 시스템 아키텍처 및 배포 환경 개요

본 프로젝트는 저사양 엣지 하드웨어(라즈베리파이 3B, 1GB RAM)의 메모리 고갈과 발열을 원천 차단하고 상용 스마트홈 수준의 확장성을 확보하기 위해 **엔터프라이즈 3-Tier 클라우드 아키텍처**를 100% 구축하여 검증을 완료하였습니다.

* **클라우드 연동 URL**: `https://dogmate-backend-1089229092493.us-central1.run.app`
* **Swagger 대화형 API 문서**: `https://dogmate-backend-1089229092493.us-central1.run.app/docs`
* **운영 비용**: Google Cloud Run(월 200만 회 무료) + GCS(5GB 무료) + FCM(무제한 무료) + Supabase(500MB 무료) = **월 0원 ($0 Always-Free)**

```text
[Client Layer] 보호자 스마트폰 모바일 앱 (iOS/Android) / 테스트용 웹 콘솔
       ↕ (HTTPS RESTful JSON API / Firebase FCM 긴급 푸시 알림)
+===================================================================================================+
|  Cloud Infrastructure ($0 Zero-Cost Architecture)                                                |
|  ├── [Compute]  Google Cloud Run (Docker Containerized Gunicorn + Flask-RESTX)                     |
|  ├── [Database] Supabase Managed PostgreSQL 15 (Session Pooler IPv4: aws-0-ap-northeast-2)        |
|  ├── [Storage]  Google Cloud Storage (버킷: gs://dogmate-0830/, 보안 스트리밍 게이트웨이)             |
|  └── [Push]     Firebase Cloud Messaging (FCM) (실시간 이상 짖음/배회 감지 시 스마트폰 팝업 푸시)        |
+===================================================================================================+
       ↕ (REST API: /api/v1/devices/telemetry, /events/bark, /commands/pending)
[Edge Layer] Raspberry Pi 3 Model B V1.2 (Linux 3-Thread Master Client Daemon)
       ├── 🧠 Edge AI       : Google YAMNet-TFLite (3.9MB 오디오 짖음 분류) + MOG2 현관문 ROI 배회 감지
       ├── 📷 Vision         : Pi Camera (CSI) ➔ 짖음/배회 감지 시 JPEG 스틸컷 즉시 캡처 및 클라우드 업로드
       ├── 🎙️ Audio Input    : USB 마이크 (16kHz 오디오 스트림 수집)
       ├── 🌡️ Sensors (I2C)  : Grove 사운드(A0), 조도(A1), 온습도(D3), 초음파(D4 간식 잔여량)
       └── ⚙️ Actuators      : SG-90 서보모터(D5 간식 투출), 스피커(음성 재생), 부저, 야간 안심 LED
```

---

## 🔌 2. 배포 완료된 REST API 엔드포인트 명세 (/docs)

모든 엔드포인트는 OpenAPI 3.0 규격을 준수하며, 모바일 앱(Client Layer)에서 즉시 사용할 수 있도록 순수 JSON DTO 및 멀티파트 규격으로 설계되었습니다:

| 분류 | HTTP | 엔드포인트 경로 | 요청 데이터 | 응답 코드 및 기능 설명 |
| :---: | :---: | :--- | :--- | :--- |
| **Health** | `GET` | `/api/v1/health` | None | `200 OK` - Supabase DB 및 GCS 연동 헬스체크 |
| **Device** | `POST` | `/api/v1/devices/telemetry` | `JSON` | `201 Created` - 온습도, 조도, 간식 잔여량 DB 적재 및 하트비트 갱신 |
| **Device** | `POST` | `/api/v1/devices/heartbeat` | `JSON` | `200 OK` - 디바이스 생존 신호 수신 및 온라인 상태 갱신 |
| **Device** | `POST` | `/api/v1/devices/events/bark` | `Multipart` | `201 Created` - 이상 짖음/배회 사진 GCS 업로드, DB 기록, FCM 긴급 푸시 |
| **Device** | `GET` | `/api/v1/devices/commands/pending`| `Query` | `200 OK` - 디바이스 미실행 원격 명령(간식 투출/음성 재생) 큐 폴링 |
| **Device** | `POST` | `/api/v1/devices/commands/ack` | `JSON` | `200 OK` - 액추에이터 실행 결과 보고 (status='completed') |
| **App** | `GET` | `/api/v1/app/status` | `Query` | `200 OK` - 실시간 연결 여부, 최신 센서 요약 단일 응답 |
| **App** | `POST` | `/api/v1/app/feed` | `JSON` | `200 OK` - 보호자 원격 수동 간식 급여 명령 큐 적재 |
| **App** | `POST` | `/api/v1/app/voice` | `Multipart` | `200 OK` - 보호자 녹음 음성(WAV) 업로드 및 스피커 재생 명령 하달 |
| **App** | `GET` | `/api/v1/app/events` | `Query` | `200 OK` - 최근 이상 짖음/배회 목록 및 보안 사진 스트리밍 URL 반환 |
| **App** | `GET` | `/api/v1/app/telemetry/history`| `Query` | `200 OK` - 24시간 실내 온습도/조도 시계열 차트용 데이터 배열 |
| **App** | `GET` | `/api/v1/app/photos/<path>` | `URL Path` | `200 OK` - 비공개 GCS 버킷의 반려견 사진을 백엔드에서 안전하게 스트리밍 |

---

## 🍓 3. 엣지 하드웨어(Edge Hardware) 및 AI 모듈 구현 현황

라즈베리파이 3B 엣지 클라이언트는 실물 키트와 개발 시뮬레이터를 100% 동시 지원하는 듀얼 모드로 구축되었습니다:

1. **환경 센서군 ([`environment.py`](../hardware/sensors/environment.py), [`sound.py`](../hardware/sensors/sound.py))**:
   - 실내 온습도(DHT11/D3), 조도(A1), 초음파(D4) 기반 간식 잔여량(0~100%) 환산 수집
   - Grove 사운드 센서(A0) 70dB 1차 소음 급증 감지
2. **액추에이터 ([`servo.py`](../hardware/actuators/servo.py), [`speaker.py`](../hardware/actuators/speaker.py), [`alerts.py`](../hardware/actuators/alerts.py))**:
   - SG-90 서보모터(D5) 180도 회전 간식 투출 및 잔여량 자동 차감
   - 보호자 음성 메시지 스피커 재생 (macOS `afplay` / Linux `aplay`, `pygame` 자동 대응)
   - 부저(D6) 비프음 및 **조도 센서 연동 야간 안심 LED 자동 점등(150 Lux 임계값, 30 Lux 히스테리시스)**
3. **카메라 및 비전 ([`camera.py`](../hardware/camera.py))**:
   - PiCamera2(CSI) / OpenCV 웹캠 스틸컷 캡처
   - 이상 짖음 및 현관문 배회 상황에 맞춘 시뮬레이션 프레임 렌더링 지원
4. **Edge AI 지능형 알고리즘 ([`yamnet_detector.py`](../hardware/ai/yamnet_detector.py), [`roi_motion_detector.py`](../hardware/ai/roi_motion_detector.py))**:
   - **Google YAMNet-TFLite (3.9MB)**: AudioSet 521 클래스 중 `Bark(70)`, `Howl(72)` 짖음 판별
   - **현관문 관심 구역(ROI) 배회 감지**: Ogata(2016) 논문 기반 출입구 영역 5초 이상 지속 체류 시 경보 트리거
5. **통합 데몬 ([`client.py`](../hardware/client.py), [`simulate.py`](../hardware/simulate.py))**:
   - 3-Thread 분기 안전 가동 및 번호 선택형 대화형 테스트 콘솔(1~7번) 제공

---

## 📊 4. E2E 기능 및 배포 환경 종합 검증 결과표 (Full Test Suite)

* **테스트 스위트 스크립트**: [`scripts/run_full_system_test.py`](../scripts/run_full_system_test.py)
* **검증 환경**: Google Cloud Run 실서버 (`https://dogmate-backend-...run.app`) + Edge Client

| 번호 | 검증 카테고리 | 테스트 항목명 | 검증 대상 | 판정 | 세부 검증 결과 및 수치 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Cloud Backend** | 인프라 헬스체크 (/health) | Cloud Run | **PASS** | HTTP 200, Supabase DB & GCS 연동 확인 |
| **2** | **Swagger OpenAPI**| API 명세 및 UI 문서 (/docs) | Cloud Run | **PASS** | HTTP 200, 11개 엔드포인트 명세 정상 로드 |
| **3** | **Web Frontend** | 모니터링 대시보드 뷰 (GET /) | Cloud Run | **PASS** | HTTP 200, HTML 템플릿 및 정적 리소스 서빙 |
| **4** | **REST API** | 센서 텔레메트리 적재 | Cloud Run | **PASS** | HTTP 201, Supabase sensor_telemetry 적재 |
| **5** | **REST API** | 생존 신호 하트비트 | Cloud Run | **PASS** | HTTP 200, devices last_heartbeat 갱신 |
| **6** | **REST API** | 이상 짖음 사진 업로드 | Cloud Run | **PASS** | HTTP 201, GCS 비공개 저장 및 bark_events 적재 |
| **7** | **REST API** | 현관문 배회(ROI) 사진 업로드 | Cloud Run | **PASS** | HTTP 201, 배회 스냅샷 클라우드 등록 완료 |
| **8** | **Security & Media**| 비공개 사진 보안 스트리밍 | Cloud Run | **PASS** | HTTP 200, JPEG 바이너리 직접 스트리밍 성공 |
| **9** | **REST API** | 원격 간식 급여 E2E 루프 | Cloud Run | **PASS** | /feed ➔ /commands 폴링 ➔ /ack 회신 완료 |
| **10**| **REST API** | 보호자 음성 업로드 및 하달 | Cloud Run | **PASS** | HTTP 200, WAV GCS 저장 ➔ PLAY_VOICE 하달 |
| **11**| **Mobile REST API**| 대시보드 종합 상태 조회 | Cloud Run | **PASS** | HTTP 200, 온라인 상태, 온습도, 간식 단일 반환 |
| **12**| **Mobile REST API**| 최근 이상행동 내역 목록 조회 | Cloud Run | **PASS** | HTTP 200, 최근 짖음/배회 기록 및 사진 리스트 |
| **13**| **Mobile REST API**| 센서 시계열 차트 데이터 조회 | Cloud Run | **PASS** | HTTP 200, 모바일 차트용 시계열 배열 반환 |
| **14**| **Hardware Sensors**| 환경 센서군 수집 | Edge Device | **PASS** | 온도 24.2℃, 습도 50.2%, 조도 358Lux, 잔여 85% |
| **15**| **Hardware Actuator**| 서보모터 간식 투출 및 차감 | Edge Device | **PASS** | SG-90 180도 회전 및 잔여량 5% 차감 정상 |
| **16**| **Hardware Actuator**| 조도 연동 야간 안심 LED | Edge Device | **PASS** | 80 Lux ➔ ON, 320 Lux ➔ OFF (히스테리시스 작동) |
| **17**| **Hardware Vision**| 카메라 스틸컷 캡처 | Edge Device | **PASS** | JPEG 표준 헤더 검증, 상황별 시각화 프레임 |
| **18**| **Edge AI** | Google YAMNet 짖음 오디오 AI | Edge Device | **PASS** | 3.9MB 모델 탑재, 짖음 감지(신뢰도 92%) 성공 |
| **19**| **Edge AI** | 현관문 배회(ROI) 모션 감지 | Edge Device | **PASS** | MOG2 배경차분 기반 현관 7.2초 체류 감지 |

**최종 검증 요약**: **총 19개 항목 중 19개 전원 합격 (성공률 100.0%, 소요시간: 35.64초)**

---

## 🔒 5. 보안 및 장애 대응 검증 내역 (Troubleshooting)

1. **GCS 비공개 버킷 사진 URL 접속 시 `AccessDenied` 문제 해결**:
   - 반려견 사생활 보호를 위해 GCS 버킷에 '공개 액세스 방지'를 유지하면서, Cloud Run 백엔드가 중간에서 인증 권한으로 이미지를 읽어와서 브라우저에 안전하게 넘겨주는 **보안 스트리밍 엔드포인트(`GET /api/v1/app/photos/<path>`)**를 구축하여 완벽히 해결.
2. **Supabase IPv6 다이렉트 주소 연결 불가 해결**:
   - 일반 IPv4 네트워크 호환을 위해 Supabase 공식 **IPv4 Session Pooler(`aws-0-ap-northeast-2.pooler.supabase.com:5432`)**로 연결 체계를 단일화하여 해결.
3. **macOS AirPlay 수신기 5000번 포트 충돌 방지**:
   - 로컬 개발 포트를 `5001`로 조정하고, Cloud Run 프로덕션 환경에서는 컨테이너 환경변수(`$PORT=8080`)를 자동 바인딩하도록 구현.

---

## 🎯 6. 결론 및 모바일 앱 연동 준비도

* **시스템 완성도**: 클라우드 인프라, 데이터베이스, REST API, 하드웨어 엣지 드라이버, 엣지 AI에 이르는 **전체 시스템이 결함 제로 상태로 배포 및 검증**되었습니다.
* **모바일 앱 준비 상태**: 본 백엔드는 모든 기능이 모바일 전용 표준 RESTful API 및 Firebase FCM 푸시 규격으로 맞춰져 있으므로, **보호자 스마트폰 모바일 앱(Flutter, React Native 등)과의 연동 개발에 즉시 착수할 수 있는 완벽한 준비 상태**를 갖추었습니다.
