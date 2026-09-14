# ☁️ PawCare IoT 구글 클라우드(GCP) 백엔드 아키텍처 및 시스템 설계 기획서
> **과목**: 국립금오공과대학교 2026-2 IoT기초설계  
> **팀원**: 김민중, 김영재  
> **인프라**: Google Cloud Platform (GCP) + Raspberry Pi 3 Model B V1.2  
> **문서 버전**: v2.0 (Google Cloud-Native 3-Tier 전환 개정판)

---

## 📌 1. GCP 클라우드 백엔드 설계 개요 및 원칙

라즈베리파이 로컬 저장(SQLite)의 한계를 탈피하여, **Google Cloud Platform(GCP)** 기반의 **완전한 엔터프라이즈 3-Tier 클라우드 IoT 아키텍처**를 구축합니다.  
라즈베리파이(Edge)는 센서 수집 및 YAMNet AI에만 전념하고, 비즈니스 로직·PostgreSQL DB·GCS 스토리지·FCM 푸시 알림은 **GCP 서버리스 클라우드**가 전담합니다.

* **실제 상용 스마트홈 아키텍처 (SmartThings/Google Home 동급)**: 집 밖(LTE/5G)에서도 언제든 완벽하게 접속 및 제어 가능한 진정한 원격 IoT 시스템 구축.
* **RPi 3B 컴퓨팅 자원 완전 해방**: 웹 서버 부하 및 DB 트랜잭션을 GCP로 이관하여, 라즈베리파이 3B(1GB RAM)의 메모리 고갈과 발열을 원천 차단하고 오디오 AI(YAMNet) 연산에 100% 집중.
* **Google AIoT 네이티브 시너지**: 엣지 AI 모델(**Google YAMNet**) + 푸시 알림(**Firebase Cloud Messaging**) + 클라우드 서버(**GCP Cloud Run**)로 이어지는 완벽한 구글 기술 스택 통일.
* **안정적인 파일 분리 저장**: SD카드 수명을 단축시키는 사진 저장 대신, 전 세계 표준 객체 스토리지인 **Google Cloud Storage (GCS)**에 안전하게 영구 적재.

---

## 🏛️ 2. 전체 GCP 3-Tier 클라우드 시스템 계층 구조

```text
[Client Layer] 보호자 스마트폰 모바일 앱 / 반응형 웹 브라우저 (LTE / 5G / Wi-Fi)
       ↕ (HTTPS REST API / WebSocket / Firebase FCM Push)
+===================================================================================================+
|  Google Cloud Platform (GCP) Backend Infrastructure                                               |
|  ├── [Compute]        Google Cloud Run (Docker Containerized FastAPI / Flask, Auto-scaling)       |
|  ├── [Database]       Google Cloud SQL for PostgreSQL (기기 정보, 센서 시계열, 짖음 이벤트, 급여 로그)  |
|  ├── [Object Storage] Google Cloud Storage (GCS Bucket: gs://pawcare-event-captures/)            |
|  └── [Messaging]      Firebase Cloud Messaging (FCM) (실시간 이상 짖음 발생 시 스마트폰 긴급 푸시 알림)   |
+===================================================================================================+
       ↕ (양방향 WebSocket: /ws/device/{id} & HTTPS REST: /api/v1/telemetry)
[Edge Device Layer] Raspberry Pi 3 Model B V1.2 (Linux Client Daemon)
       ├── 🧠 Edge AI       : Google YAMNet-TFLite (3.8MB, 오디오 짖음 분류 50ms 실시간 추론)
       ├── 📷 Vision         : Pi Camera (CSI) ➔ 짖음 감지 시 캡처 후 GCP GCS로 직접/중계 멀티파트 업로드
       ├── 🎙️ Audio Input    : USB 마이크 (16kHz 오디오 스트림 수집)
       ├── 🌡️ Sensors (I2C)  : Grove 사운드(A0), 조도(A1), 온습도(D3), 초음파(D4 간식 잔여량)
       └── ⚙️ Actuators      : SG-90 서보모터(D5 간식 투출), 스피커(음성 메시지 재생), LED, 부저
```

---

## 🛠️ 3. GCP 인프라 및 기술 스택 상세 (GCP Tech Stack)

| GCP 컴포넌트 | 선정 기술 및 사양 | 선정 이유 및 세부 역할 |
| :--- | :--- | :--- |
| **Cloud Compute** | **Google Cloud Run** (또는 GCE e2-micro) | 서버리스 컨테이너(Docker), 요청 시 자동 확장, 월 200만 회 호출 무료, 초저비용 무중단 운영 |
| **Cloud Database** | **Cloud SQL (PostgreSQL 15)**<br>*(또는 GCP VM 내 PostgreSQL)* | SQLite 파일 동시성 제약 해결, 관계형 정합성 및 시계열 센서 데이터(온습도/조도) 효율적 인덱싱 |
| **Object Storage** | **Google Cloud Storage (GCS)** | 짖음 감지 사진 파일 전용 버킷, 고유 URL 발급 및 CDN 초고속 로딩, SD카드 쓰기 수명 보호 |
| **Push Notification** | **Firebase Cloud Messaging (FCM)** | 구글 네이티브 푸시 서비스, 백그라운드 상태의 보호자 스마트폰으로 사진 포함 실시간 팝업 경보 |
| **Real-time Comm** | **WebSocket (Socket.IO)** | 클라우드 ⇄ 라즈베리파이 간 영구 TCP 파이프 연결, 원격 [간식 주기] 명령 즉시 전달(지연 < 50ms) |
| **Edge Runtime** | Python 3.10 + `tflite-runtime` | 라즈베리파이 3B 전용 엣지 클라이언트 데몬, 무거운 웹서버 부담 없이 센서 수집 및 YAMNet 전념 |

---

## ⚙️ 4. 엔드투엔드(End-to-End) 데이터 처리 파이프라인

### ① 엣지 ➔ 클라우드: 센서 텔레메트리 및 짖음 감지 업로드 파이프라인
* **정기 텔레메트리 (60초 주기)**: 라즈베리파이가 온습도, 조도, 간식 잔여량(초음파 이동평균)을 수집하여 GCP Cloud Run 엔드포인트(`POST /api/v1/devices/telemetry`)로 배치 전송 ➔ Cloud SQL에 시계열 적재.
* **이상 짖음 긴급 이벤트**:
  1. Grove 사운드센서 70dB 감지 ➔ USB 마이크 0.975초 수집 ➔ **YAMNet TFLite 추론**.
  2. `Bark(71번)` 확률 0.35 이상 시 카메라 캡처 ➔ `POST /api/v1/devices/events/bark`로 이미지 멀티파트 전송.
  3. GCP Cloud Run이 수신 이미지를 **Google Cloud Storage(GCS)**에 저장(URL 생성) ➔ Cloud SQL에 이벤트 기록.
  4. GCP가 **Firebase Cloud Messaging(FCM)**을 트리거하여 보호자 스마트폰에 *"[경보] 반려견 짖음 감지! (사진 첨부)"* 푸시 발송.

### ② 클라우드 ➔ 엣지: 원격 제어 명령 (간식 투출 & Push-to-Talk 음성)
* **양방향 WebSocket 유지**: 라즈베리파이가 부팅 시 GCP Cloud Run과 `/ws/device/{device_id}` 웹소켓 파이프를 상시 연결.
* **원격 간식 급여**: 보호자가 앱에서 [간식 주기] 클릭 ➔ GCP로 HTTP POST ➔ GCP가 연결된 WebSocket으로 `{"command": "DISPENSE_TREAT"}` 푸시 ➔ 라즈베리파이 서보모터(SG-90) 180도 회전 및 간식 투출.
* **Push-to-Talk 음성 송출**: 보호자가 앱에서 녹음한 음성(WAV Blob)을 GCP로 업로드 ➔ 라즈베리파이가 다운로드 즉시 `pygame.mixer` 비동기 스레드로 키트 스피커 출력.

---

## 🗄️ 5. 클라우드 데이터베이스(DB) 스키마 설계 (PostgreSQL on GCP)

```sql
-- 1. 디바이스 등록 및 상태 관리 테이블
CREATE TABLE devices (
    device_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    owner_email VARCHAR(100) NOT NULL,
    status VARCHAR(16) DEFAULT 'offline', -- 'online', 'offline'
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 환경 센서 시계열 텔레메트리 테이블
CREATE TABLE sensor_telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(32) REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    temperature REAL,
    humidity REAL,
    light_level INT,
    treat_percent INT
);
CREATE INDEX idx_telemetry_device_time ON sensor_telemetry (device_id, timestamp DESC);

-- 3. 이상 짖음 감지 및 GCS 이미지 링크 테이블
CREATE TABLE bark_events (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(32) REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    sound_db INT,
    confidence REAL,
    gcs_image_url TEXT,
    is_resolved BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_bark_events_device ON bark_events (device_id, timestamp DESC);

-- 4. 간식 투출 이력 감사 로그 테이블
CREATE TABLE feed_logs (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(32) REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    trigger_type VARCHAR(20) DEFAULT 'manual', -- 'manual', 'schedule'
    status VARCHAR(20) DEFAULT 'success'
);
```

---

## 🔌 6. 핵심 REST API 엔드포인트 명세서 (GCP Cloud Run)

| 구분 | 메서드 | 엔드포인트 | 요청 Body / Param | 응답 (Response JSON) | 설명 |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **Device ➔ GCP** | `POST` | `/api/v1/devices/telemetry` | `{"temp": 24.1, "hum": 51, "treat": 85}` | `{"status": "recorded"}` | 라즈베리파이 센서 주기적 배치 전송 |
| **Device ➔ GCP** | `POST` | `/api/v1/devices/events/bark` | `multipart/form-data` (image, conf) | `{"event_id": 108, "gcs_url": "https://..."}` | 짖음 감지 시 사진 및 AI 결과 업로드 |
| **Client ➔ GCP** | `GET` | `/api/v1/app/status` | `?device_id=rpi3b_01` | `{"online": true, "temp": 24.1, "treat_pct": 85}` | 실시간 대시보드 상태 조회 |
| **Client ➔ GCP** | `POST` | `/api/v1/app/feed` | `{"device_id": "rpi3b_01"}` | `{"success": true, "message": "명령 전송 완료"}` | 스마트폰 원격 간식 급여 트리거 |
| **Client ➔ GCP** | `POST` | `/api/v1/app/voice` | `multipart/form-data` (voice.wav) | `{"success": true, "dispatched": true}` | Push-to-Talk 보호자 음성 업로드 |
| **Client ➔ GCP** | `GET` | `/api/v1/app/events` | `?device_id=rpi3b_01&limit=10` | `[{"id": 108, "time": "...", "url": "https://..."}]` | 최근 이상 짖음 이벤트 및 사진 목록 |

---

## 🔒 7. 보안, 인증 및 비용 최적화 전략 (GCP Free-Tier $0 설계)

1. **IAM 서비스 계정 & Signed URL 보안**:
   * GCS 버킷을 퍼블릭으로 열지 않고, GCP Cloud Run이 인증된 사용자에게만 유효기간 15분의 **V4 서명된 URL(Signed URL)**을 발급하여 외부 유출 원천 차단.
   * 라즈베리파이는 안전한 `X-Device-Token` 헤더를 통해 GCP와 상호 인증.
2. **GCP $0 비용 최적화 (Always Free & 크레딧 활용)**:
   * **Cloud Run**: 월 200만 회 호출 및 36만 GiB-초 vCPU 무료 (프로젝트 사용량 100% 무료 범위 내 커버).
   * **Cloud Storage (GCS)**: 월 5GB 스토리지 무료 (사진 1장당 150KB 기준 약 33,000장 보관 가능).
   * **Firebase FCM**: 무제한 푸시 알림 100% 무료.

---

## 🎯 8. 심사위원(교수님) 평가 어필 포인트

* **소프트웨어 설계 역량 (25점 만점)**: 단순 아두이노/라즈베리파이 토이 프로젝트를 넘어선 **Google Cloud 기반 마이크로서비스(MSA) & Serverless 3-Tier 아키텍처** 설계.
* **데이터 정합성 및 시계열 분석**: PostgreSQL 관계형 DB를 활용한 안정적인 텔레메트리 파이프라인 구축.
* **하이브리드 신뢰성 (40점 만점)**: 클라우드 장애 시에도 라즈베리파이 엣지에서 자율 구동되는 결함 허용(Fault-tolerant) 메커니즘.
