# ☁️ PawCare IoT 100% 무료 클라우드 백엔드 아키텍처 및 시스템 설계 기획서
> **과목**: 국립금오공과대학교 2026-2 IoT기초설계  
> **팀원**: 김민중, 김영재  
> **인프라**: GCP (Cloud Run, GCS, FCM) + Supabase (PostgreSQL 15)  
> **운영 비용**: **월 0원 (Always Free & 크레딧 차감 0원 설계)**  
> **문서 버전**: v2.1 ($0 Zero-Cost Enterprise 3-Tier)

---

## 📌 1. 100% 무료 클라우드 백엔드 설계 개요 및 원칙

유료 과금 위험이 있는 `Cloud SQL`을 평생 완전 무료인 **Supabase (PostgreSQL 15)**로 대체하고, 서버(**Google Cloud Run**), 파일 저장소(**Google Cloud Storage**), 푸시 알림(**Firebase FCM**)은 구글 공식 **Always Free 티어**를 적용하여 **크레딧 차감 0원, 실제 카드 결제 0원의 엔터프라이즈 3-Tier 클라우드 IoT 백엔드**를 구축합니다.

* **과금 위험 제로 (100% Zero-Cost)**: 구글 클라우드의 영구 무료 티어(Always Free)와 Supabase 무료 플랜(500MB DB)을 조합하여 학기 내내 단 1원의 추가 비용도 발생하지 않도록 설계.
* **엔터프라이즈 3-Tier 분리 구축**: 라즈베리파이(Edge)는 센서 수집 및 YAMNet AI에만 전념하고, 비즈니스 로직 및 DB 연산은 외부 클라우드가 전담하여 RPi 3B(1GB RAM)의 메모리 고갈 원천 차단.
* **실제 상용 스마트홈(LTE/5G) 환경 완벽 지원**: 학교 Wi-Fi나 공유기 포트포워딩 없이도 외부 인터넷 어디서든 스마트폰으로 즉시 접속 및 원격 제어 가능.
* **PostgreSQL 15 표준 정규화**: SQLite 파일 동시성 제약을 극복하고, 관계형 정합성과 시계열 센서 텔레메트리를 고속 인덱싱 쿼리.

---

## 🏛️ 2. 전체 3-Tier 클라우드 시스템 계층 구조

```text
[Client Layer] 보호자 스마트폰 모바일 앱 / 반응형 웹 브라우저 (LTE / 5G / Wi-Fi)
       ↕ (HTTPS REST API / WebSocket / Firebase FCM Push)
+===================================================================================================+
|  Cloud Backend Infrastructure (100% Free Tier Architecture)                                       |
|  ├── [Compute Server]  Google Cloud Run (Docker Containerized FastAPI / Flask, 월 200만 회 무료)   |
|  ├── [Cloud Database]  Supabase Managed PostgreSQL 15 (500MB 용량 평생 무료, 실시간 텔레메트리 DB)     |
|  ├── [Object Storage]  Google Cloud Storage (GCS Bucket: gs://pawcare-event-captures/, 월 5GB 무료)   |
|  └── [Push Messaging]  Firebase Cloud Messaging (FCM) (실시간 이상 짖음 발생 시 스마트폰 무료 푸시)        |
+===================================================================================================+
       ↕ (양방향 WebSocket: /ws/device/{id} & HTTPS REST: /api/v1/devices/telemetry)
[Edge Device Layer] Raspberry Pi 3 Model B V1.2 (Linux Client Daemon)
       ├── 🧠 Edge AI       : Google YAMNet-TFLite (3.8MB, 오디오 짖음 분류 50ms 실시간 추론)
       ├── 📷 Vision         : Pi Camera (CSI) ➔ 짖음 감지 시 캡처 후 GCP GCS로 직접/중계 멀티파트 업로드
       ├── 🎙️ Audio Input    : USB 마이크 (16kHz 오디오 스트림 수집)
       ├── 🌡️ Sensors (I2C)  : Grove 사운드(A0), 조도(A1), 온습도(D3), 초음파(D4 간식 잔여량)
       └── ⚙️ Actuators      : SG-90 서보모터(D5 간식 투출), 스피커(음성 메시지 재생), LED, 부저
```

---

## 🛠️ 3. 클라우드 컴포넌트별 무료 티어 및 비용 검증

| 컴포넌트 | 선정 서비스 및 사양 | 무료 티어 제공량 | 예상 월 비용 |
| :--- | :--- | :--- | :---: |
| **Cloud Compute** | **Google Cloud Run** | 월 200만 회 호출, 36만 GiB-초 vCPU 무료 | **$0 (0원)** |
| **Cloud Database** | **Supabase (PostgreSQL 15)** | 500MB DB 용량 평생 무료 (Cloud SQL 대체) | **$0 (0원)** |
| **Object Storage** | **Google Cloud Storage (GCS)** | 월 5GB 스토리지, 5,000회 쓰기 무료 | **$0 (0원)** |
| **Push Notification** | **Firebase Cloud Messaging** | 무제한 푸시 알림 100% 무료 | **$0 (0원)** |
| **Edge Runtime** | Raspberry Pi 3B (Linux Daemon) | 로컬 하드웨어 구동 (YAMNet TFLite) | **$0 (0원)** |

---

## ⚙️ 4. 엔드투엔드(End-to-End) 데이터 처리 파이프라인

### ① 엣지 ➔ 클라우드: 센서 텔레메트리 및 짖음 감지 업로드 파이프라인
* **정기 텔레메트리 (60초 주기)**: 라즈베리파이가 온습도, 조도, 간식 잔여량(초음파 이동평균)을 수집하여 GCP Cloud Run 엔드포인트(`POST /api/v1/devices/telemetry`)로 배치 전송 ➔ Supabase PostgreSQL에 시계열 적재.
* **이상 짖음 긴급 이벤트**:
  1. Grove 사운드센서 70dB 감지 ➔ USB 마이크 0.975초 수집 ➔ **YAMNet TFLite 추론**.
  2. `Bark(71번)` 확률 0.35 이상 시 카메라 캡처 ➔ `POST /api/v1/devices/events/bark`로 이미지 멀티파트 전송.
  3. GCP Cloud Run이 수신 이미지를 **Google Cloud Storage(GCS)**에 저장(URL 생성) ➔ Supabase DB에 이벤트 기록.
  4. GCP가 **Firebase Cloud Messaging(FCM)**을 트리거하여 보호자 스마트폰에 *"[경보] 반려견 짖음 감지! (사진 첨부)"* 푸시 발송.

### ② 클라우드 ➔ 엣지: 원격 제어 명령 (간식 투출 & Push-to-Talk 음성)
* **양방향 WebSocket 유지**: 라즈베리파이가 부팅 시 GCP Cloud Run과 `/ws/device/{device_id}` 웹소켓 파이프를 상시 연결.
* **원격 간식 급여**: 보호자가 앱에서 [간식 주기] 클릭 ➔ GCP로 HTTP POST ➔ GCP가 연결된 WebSocket으로 `{"command": "DISPENSE_TREAT"}` 푸시 ➔ 라즈베리파이 서보모터(SG-90) 180도 회전 및 간식 투출.
* **Push-to-Talk 음성 송출**: 보호자가 앱에서 녹음한 음성(WAV Blob)을 GCP로 업로드 ➔ 라즈베리파이가 다운로드 즉시 `pygame.mixer` 비동기 스레드로 키트 스피커 출력.

---

## 🗄️ 5. 클라우드 데이터베이스(DB) 스키마 설계 (PostgreSQL 15 on Supabase)

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

## 🔒 7. 보안, 인증 및 비용 최적화 전략 (100% Free-Tier $0 설계)

1. **IAM 서비스 계정 & Signed URL 보안**:
   * GCS 버킷을 퍼블릭으로 열지 않고, GCP Cloud Run이 인증된 사용자에게만 유효기간 15분의 **V4 서명된 URL(Signed URL)**을 발급하여 외부 유출 원천 차단.
   * 라즈베리파이는 안전한 `X-Device-Token` 헤더를 통해 GCP와 상호 인증.
2. **$0 무과금 안전장치**:
   * **Cloud Run**: 인스턴스 최소 개수를 0개(`min-instances=0`)로 설정하여 요청이 없을 때 자원 점유율 0, 비용 0원 유지.
   * **Supabase**: 신용카드 등록 없이 이메일 인증만으로 500MB 무료 DB 영구 사용 (초과 과금 원천 불가능).
   * **GCS**: 무료 티어 리전(`us-central1`)에 버킷 생성하여 월 5GB 완전 무료 적용.
