# 🌐 PawCare IoT 백엔드 아키텍처 및 시스템 설계 기획서
> **과목**: 국립금오공과대학교 2026-2 IoT기초설계  
> **팀원**: 김민중, 김영재  
> **타겟 보드**: Raspberry Pi 3 Model B V1.2 (1GB RAM)  
> **문서 버전**: v1.0 (2026-09-14)

---

## 📌 1. 백엔드 설계 개요 및 핵심 원칙 (Core Principles)

Raspberry Pi 3B의 1GB RAM 제약 조건 하에서 **실시간 하드웨어 제어(센서·카메라·서보모터)**와 **웹 서비스(REST API·MJPEG 스트리밍·Push-to-Talk)**, **Edge AI(YAMNet TFLite)**를 지연 없이 구동하기 위한 **경량 멀티스레드 기반 Flask 비동기 백엔드 아키텍처** 명세서입니다.

* **저지연 & 경량성 (Low-latency & Lightweight)**: 무거운 웹 프레임워크 대신 **Flask 3.x**를 채택하고 메모리 State 캐싱 및 비동기 스레드 풀을 적용하여 메모리 점유율을 30MB 수준으로 억제.
* **비동기 격리 (Thread Isolation)**: 웹 요청(HTTP), 센서 수집(I2C), 카메라 스트리밍, 오디오 AI 추론이 상호 블로킹(Blocking) 없이 독립 스레드로 동작.
* **실시간 폐루프 (Closed-loop Feedback)**: 짖음 감지 ➔ 웹 실시간 경보 ➔ 원격 음성/간식 제어 ➔ 결과 피드백 전 과정을 1초 이내 전송 보장.
* **안정성 및 자원 락 (Thread-Safe Mutex Lock)**: 카메라(CSI)와 서보모터(PWM), 오디오 장치 동시 접근 시 충돌을 방지하는 상호 배제(Lock) 체계 구축.

---

## 🏛️ 2. 전체 백엔드 시스템 계층 구조 (Layered Architecture)

```text
[Client Layer] 보호자 모바일 / 반응형 웹 브라우저 (HTML5 Dashboard / MediaRecorder Audio / Fetch API / MJPEG Viewer)
       ↕ (HTTP REST / Server-Sent Events / MJPEG Video Stream)
[Flask Core]   Web Server (Port: 5000)
       ├── API Router: /api/status, /api/feed, /api/voice-message, /api/logs, /api/stream
       ├── Video Streamer: VideoCameraGenerator (MJPEG multipart/x-mixed-replace 640x480 @ 15fps)
       └── Shared State: SystemState Cache (Thread-Safe with threading.Lock)
       ↕ (Internal Thread Dispatch & Mutex)
[Background Workers]
       ├── [Worker 1] Sensor Polling Thread : GrovePi I2C 1초 주기 수집, 초음파 이동평균 필터링, 야간 자동 LED
       ├── [Worker 2] Event AI Thread      : 70dB 초과 시 구동, YAMNet TFLite 짖음 검증(50ms), 카메라 스틸컷 캡처
       ├── [Worker 3] Audio Player Queue   : MediaRecorder 음성 수신 즉시 비동기 스레드 pygame.mixer 스피커 재생
       └── [Database] SQLite3 (WAL Mode)   : sensor_logs (환경), bark_events (이상감지), feed_history (급여)
       ↕ (Hardware Driver Abstraction)
[Hardware]    Raspberry Pi 3B + GrovePi+ (Camera CSI, USB Mic, Sound, Light, Temp/Hum, Ultrasonic, SG-90, Speaker, LED)
```

---

## 🛠️ 3. 백엔드 기술 스택 상세 (Backend Tech Stack)

| 구분 | 선정 기술 및 라이브러리 | 선정 이유 및 세부 역할 |
| :--- | :--- | :--- |
| **Web Framework** | **Python Flask 3.x** | 강의 11~12주차 커리큘럼 100% 일치, 초경량 메모리 점유(~30MB), 빠른 REST API 구성 |
| **Concurrency** | `threading.Thread`, `queue.Queue` | 센서 수집, 비디오 캡처, 오디오 재생의 비동기 분리 처리 (GIL 병목 방지) |
| **Edge AI Runtime** | `tflite-runtime` (YAMNet) | 무거운 TensorFlow 없이 3.8MB 모델 구동 (추론 시간: RPi 3B 기준 약 50ms) |
| **Computer Vision** | `OpenCV (cv2-headless)` | GUI 없는 경량 빌드, MJPEG 인코딩 및 스틸컷 캡처, 현관문 ROI 감지 |
| **Audio Processing** | `sounddevice`, `pygame.mixer` | USB 마이크 16kHz 오디오 버퍼 캡처 및 보호자 음성 메시지(WAV) 즉각 출력 |
| **Embedded Driver** | `grovepi`, `RPi.GPIO` | GrovePi+ I2C 통신 및 하드웨어 PWM 서보모터 정밀 각도 제어 |
| **Database** | **SQLite3** (WAL Mode) | 별도 서버 없는 파일 기반 경량 적재, Write-Ahead Logging으로 동시성 확보 |

---

## ⚙️ 4. 멀티스레드 기반 비동기 작업 파이프라인 (RPi 3B 최적화)

### ① 센서 상시 수집 워커 (Sensor Polling Thread)
* **수행 주기**: 1초 간격 (`time.sleep(1.0)`)
* **동작 내용**: 사운드(A0), 조도(A1), 온습도(D3), 초음파(D4) 센서 값을 순차 읽기.
* **노이즈 필터링**: 초음파 센서 값은 **이동 평균 필터(Moving Average, 최근 5회 평균)**를 거쳐 오차를 보정한 뒤 간식통 잔여량(%)으로 환산.
* **야간 자동 조명**: 조도 센서 측정값이 기준치(200 미만)일 경우 즉시 LED 모듈(D2) On/Off 제어.
* **데이터 캐싱**: 전역 `SystemState` 딕셔너리에 최신 값을 갱신하여 클라이언트 API 호출 시 즉시 응답 (I2C 지연 시간 0ms 화).

### ② 2-Step 지능형 AI 이벤트 워커 (Event-driven AI Thread)
* **평상시**: 백그라운드에서 CPU 점유율 0% 상태로 대기.
* **1차 트리거 (데시벨)**: 사운드 센서 측정값이 70dB(임계치 약 650)을 초과하는 순간 워커 기동.
* **2차 검증 (Edge AI)**: USB 마이크로 0.975초 오디오 버퍼를 수집하여 `YAMNet TFLite` 모델에 입력.
* **결과 판정**: `Bark(71번)` 확률이 0.35 이상일 때만 카메라를 호출하여 스냅샷(`event_YYYYMMDD_HHMMSS.jpg`) 캡처 후 DB 기록 및 웹 실시간 경보 플래그 활성화. (공사/생활 소음 시 즉시 무시)

### ③ 비디오 스트리밍 제너레이터 (MJPEG Streaming Worker)
* **동작 방식**: 클라이언트가 `/api/stream` 접속 시 제너레이터 함수(`yield`)를 통해 `multipart/x-mixed-replace` 프로토콜로 JPEG 프레임 연속 전송.
* **프레임 최적화**: 네트워크 대역폭과 RPi 부하를 줄이기 위해 **해상도 640x480, 15 FPS**로 제한.
* **카메라 뮤텍스 락**: AI 이벤트 캡처 시 카메라 모듈 충돌을 막기 위해 `camera_lock`을 통해 접근 순서 보장.

### ④ Push-to-Talk 음성 재생 큐 (Audio Playback Worker)
* **동작 방식**: 클라이언트에서 업로드된 음성 Blob(WAV) 파일을 `/tmp/voice.wav`에 저장 후 비동기 재생 큐(Queue)에 삽입.
* **출력 제어**: 메인 스레드를 멈추지 않고 `pygame.mixer` 백그라운드 스레드에서 스피커로 출력.

---

## 🗄️ 5. 데이터베이스(DB) 스키마 설계 (SQLite3)

SD카드 수명 보호와 빠른 I/O를 위해 **WAL(Write-Ahead Logging) 모드**를 적용한 경량 테이블 3종을 운영합니다.

```sql
-- 1. 환경 센서 시계열 로그
CREATE TABLE sensor_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature REAL,
    humidity REAL,
    light_level INTEGER,
    treat_percent INTEGER
);

-- 2. 짖음 감지 이상 이벤트 로그
CREATE TABLE bark_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    sound_db INTEGER,
    confidence REAL,
    image_filename TEXT,
    is_dismissed BOOLEAN DEFAULT 0
);

-- 3. 간식 투출 이력 로그
CREATE TABLE feed_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    trigger_type TEXT, -- 'manual' or 'schedule'
    amount_steps INTEGER,
    status TEXT
);
```

---

## 🔌 6. 핵심 REST API 및 스트리밍 엔드포인트 명세

| 메서드 | 엔드포인트 | 요청 파라미터 / Body | 응답 형식 (JSON) | 설명 |
| :---: | :--- | :--- | :--- | :--- |
| `GET` | `/api/status` | None | `{"temp":24.2, "hum":52, "light":420, "treat_pct":85, "night_mode":false, "alert":false}` | 실시간 대시보드 상태 조회 (0ms 캐시 응답) |
| `GET` | `/api/stream` | None | `multipart/x-mixed-replace; boundary=frame` | 실시간 MJPEG 640x480 비디오 스트림 |
| `POST` | `/api/feed` | `{"portion": 1}` | `{"success": true, "message": "간식 투출 완료", "remaining_pct": 80}` | 서보모터 구동 및 간식 1회 물리 배출 |
| `POST` | `/api/voice-message` | `multipart/form-data` (file) | `{"success": true, "message": "음성 재생 완료", "duration_sec": 1.8}` | 보호자 Push-to-Talk 음성 파일 수신 및 스피커 비동기 재생 |
| `GET` | `/api/events/latest` | `?limit=10` | `[{"id":42, "time":"14:20:05", "confidence":0.88, "img_url":"/static/captures/ev_42.jpg"}]` | 최근 이상 짖음 이벤트 및 사진 목록 조회 |
| `GET` | `/api/history/environment`| `?range=24h` | `[{"time":"12:00", "temp":24.1, "hum":50}, ...]` | 24시간 온습도 변화 시계열 차트 데이터 |

---

## 📡 7. 실시간 경보 전송 메커니즘 (Server-Sent Events)

* **Server-Sent Events (SSE: `/api/events/live`) 채택**:
  * 무거운 웹소켓 라이브러리 의존성 없이 표준 HTTP 단방향 스트림으로 **라즈베리파이 ➔ 웹 브라우저 실시간 푸시** 구현.
  * **동작 흐름**: 평상시 연결 유지 ➔ AI가 짖음 판정 시 `data: {"type": "BARK_ALERT", "img": "..."}\n\n` 전송 ➔ 브라우저가 즉시 팝업 배너 및 비프음 발생.
  * **폴백(Fallback)**: 브라우저 환경 제약 시 **2초 주기 폴링(Polling: `/api/status`)**으로 자동 전환되어 100% 안정적 동작 보장.

---

## 🌐 8. 네트워크 환경 및 외부 접속 전략 (Network Deployment)

| 구분 | 로컬 모드 (발표 시연용 권장) | 원격 모드 (실제 외출 환경) |
| :--- | :--- | :--- |
| **네트워크 구성** | 스마트폰 모바일 핫스팟 (LTE/5G) 폐쇄망 | 가정용 공유기(Wi-Fi) + 무료 보안 터널링 |
| **접속 주소** | `http://192.168.43.x:5000` (또는 `http://pawcare.local:5000`) | `https://pawcare-iot.trycloudflare.com` (Cloudflare Tunnel) |
| **특징 및 장점** | 학교 방화벽/인터넷 장애 영향 0%, 지연시간 5ms 이하 초저지연 시연 | 포트포워딩 불필요, 어디서든 안전한 HTTPS 암호화 원격 제어 |

---

## 🛡️ 9. 시스템 안정성 및 결함 허용 (Fail-Safe & Watchdog)

1. **모터 과열 및 기어 보호**: 서보모터는 간식 1회 투출(0도 ➔ 180도 ➔ 0도) 후 **즉시 PWM 신호를 분리(`pwm.stop()`)**하여 대기 전력 소모와 지터링(떨림/과열) 원천 방지.
2. **연속 간식 급여 방지 (쿨다운)**: 반려견 과식 및 기계 걸림을 방지하기 위해 간식 투출 후 **10초간 재호출 잠금(Cooldown Lock)** 적용.
3. **SD카드 수명 보존**: 센서 로그는 매초 쓰지 않고 메모리 버퍼에 유지 후 10분 단위 일괄 적재(Batch Insert), 로그 파일 일주일 단위 자동 순환.
