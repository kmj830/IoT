# 🔌 멍메이트(DogMate) RESTful API 규격서 (Language-Agnostic)

본 문서는 특정 프로그래밍 언어나 프레임워크(Flutter, React Native, Swift, Kotlin, React, Vue 등)에 종속되지 않는 **표준 HTTP/REST API 규격서**입니다.  
클라이언트 개발 시 어떤 기술 스택을 사용하든 본 명세의 표준 HTTP 요청 및 JSON 스키마를 그대로 호출하시면 됩니다.

---

## 🌐 1. 공통 환경 및 헤더

* **Production Base URL**: `https://dogmate-backend-1089229092493.us-central1.run.app`
* **Local Development Base URL**: `http://localhost:5001`
* **Interactive Swagger UI**: `https://dogmate-backend-1089229092493.us-central1.run.app/docs`
* **OpenAPI 3.0 Schema**: `https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/swagger.json`
* **기본 Target Device ID**: `dogmate-rpi3b-01`
* **CORS**: `Access-Control-Allow-Origin: *` 적용 완료 (모든 출처 통신 허용)

---

## 📡 2. 클라이언트 연동 핵심 REST API

### ① 실시간 홈 대시보드 상태 조회 (Device Status Summary)
디바이스의 온라인/오프라인 여부, 최신 환경 센서값, 간식 잔여량, 최근 이상 짖음 정보를 한 번에 반환합니다.

* **Method**: `GET`
* **Path**: `/api/v1/app/status`
* **Query Parameters**:
  * `device_id` (string, 필수): 조회할 디바이스 식별자 (기본값: `dogmate-rpi3b-01`)
* **cURL Example**:
  ```bash
  curl -X GET "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/status?device_id=dogmate-rpi3b-01"
  ```
* **Success Response (`200 OK`)**:
  ```json
  {
    "device_id": "dogmate-rpi3b-01",
    "name": "우리집 멍메이트 키트",
    "online": true,
    "last_heartbeat": "2026-09-15T04:46:05.123456+00:00",
    "telemetry": {
      "temperature": 24.5,
      "humidity": 53.0,
      "light_level": 340,
      "treat_percent": 80,
      "measured_at": "2026-09-15T04:46:05.123456+00:00"
    },
    "latest_bark_event": {
      "timestamp": "2026-09-15T04:46:10.000000+00:00",
      "sound_db": 84,
      "confidence": 0.91,
      "image_url": "/api/v1/app/photos/events/dogmate-rpi3b-01/4cd76aea.jpg"
    }
  }
  ```
* **Response Fields**:
  * `online` (boolean): 디바이스 연결 상태 (`true`: 온라인, `false`: 오프라인)
  * `telemetry.temperature` (float): 실내 온도 (℃)
  * `telemetry.humidity` (float): 실내 습도 (%)
  * `telemetry.light_level` (int): 실내 조도 (Lux)
  * `telemetry.treat_percent` (int): 간식통 잔여량 비율 (0 ~ 100%)
  * `latest_bark_event` (object | null): 최근 발생한 이상행동 정보 (없을 시 `null`)

---

### ② 원격 간식 급여 요청 (Dispense Treat Command)
보호자가 버튼을 눌러 디바이스의 간식 투출 서보모터를 1회 물리 회전시킵니다.

* **Method**: `POST`
* **Path**: `/api/v1/app/feed`
* **Headers**: `Content-Type: application/json`
* **Request Body (JSON)**:
  ```json
  {
    "device_id": "dogmate-rpi3b-01",
    "amount": 1
  }
  ```
* **cURL Example**:
  ```bash
  curl -X POST "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/feed" \
       -H "Content-Type: application/json" \
       -d '{"device_id": "dogmate-rpi3b-01", "amount": 1}'
  ```
* **Success Response (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "간식 투출 명령이 디바이스(dogmate-rpi3b-01)로 전송 대기열에 등록되었습니다.",
    "command_id": 3
  }
  ```
  *(디바이스가 명령을 수신하여 서보모터를 180도 회전시키고 간식 잔여량을 자동 차감합니다.)*

---

### ③ Push-to-Talk 음성 메시지 전송 (Send Voice Comfort Message)
보호자가 스마트폰/브라우저 마이크로 녹음한 음성 파일을 서버에 업로드하여 디바이스 스피커로 즉시 출력합니다.

* **Method**: `POST`
* **Path**: `/api/v1/app/voice`
* **Headers**: `Content-Type: multipart/form-data`
* **Request FormData**:
  * `device_id` (text, 필수): `dogmate-rpi3b-01`
  * `voice` (binary file, 필수): 녹음된 오디오 파일 (`.wav` 권장, `.m4a` / `.mp3` 가능)
* **cURL Example**:
  ```bash
  curl -X POST "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/voice" \
       -F "device_id=dogmate-rpi3b-01" \
       -F "voice=@my_voice.wav;type=audio/wav"
  ```
* **Success Response (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "음성 파일이 안전하게 업로드되었으며 재생 명령이 대기열에 등록되었습니다.",
    "command_id": 4,
    "voice_url": "/api/v1/app/photos/voices/dogmate-rpi3b-01/ca59e8.wav"
  }
  ```

---

### ④ 이상행동(짖음 / 현관문 배회) 피드 목록 조회 (Event History)
YAMNet AI 짖음 감지 및 비전 AI 현관문 배회(ROI) 감지 이력을 역순(최신순)으로 반환합니다.

* **Method**: `GET`
* **Path**: `/api/v1/app/events`
* **Query Parameters**:
  * `device_id` (string, 필수): `dogmate-rpi3b-01`
  * `limit` (int, 선택): 조회할 이벤트 수 (기본값: `10`)
* **cURL Example**:
  ```bash
  curl -X GET "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/events?device_id=dogmate-rpi3b-01&limit=10"
  ```
* **Success Response (`200 OK`)**:
  ```json
  [
    {
      "id": 5,
      "timestamp": "2026-09-15T04:46:12.821000+00:00",
      "sound_db": 52,
      "confidence": 0.96,
      "image_url": "/api/v1/app/photos/events/dogmate-rpi3b-01/door_pacing_5.jpg",
      "is_resolved": false
    },
    {
      "id": 4,
      "timestamp": "2026-09-15T04:46:08.512000+00:00",
      "sound_db": 84,
      "confidence": 0.91,
      "image_url": "/api/v1/app/photos/events/dogmate-rpi3b-01/bark_4.jpg",
      "is_resolved": false
    }
  ]
  ```
* **Response Fields**:
  * `id` (int): 이벤트 고유 식별 번호
  * `timestamp` (ISO 8601 string): 발생 시각 (UTC)
  * `sound_db` (int): 감지 당시 실내 소음 데시벨(dB)
  * `confidence` (float): AI 판정 신뢰도 (0.0 ~ 1.0)
  * `image_url` (string): 현장 캡처 스틸컷 보안 스트리밍 상대 경로

---

### ⑤ 비공개 보안 캡처 사진 스트리밍 (Secure Photo Stream)
비공개 클라우드 스토리지에 보관된 사진을 클라이언트 애플리케이션으로 안전하게 전달합니다.

* **Method**: `GET`
* **Path**: `/api/v1/app/photos/<path:blob_name>`
* **Full URL Pattern**: `https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/photos/...`
* **cURL Example**:
  ```bash
  curl -X GET "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/photos/events/dogmate-rpi3b-01/bark_4.jpg" \
       -o snapshot.jpg
  ```
* **Success Response (`200 OK`)**:
  * `Content-Type`: `image/jpeg`
  * `Cache-Control`: `public, max-age=3600`
  * Body: JPEG 이미지 바이너리 (모바일/웹의 이미지 위젯에서 URL을 바로 소스로 사용 가능)

---

### ⑥ 24시간 센서 통계 시계열 데이터 조회 (Telemetry History)
차트(Chart) 컴포넌트에 바인딩할 수 있도록 최근 온습도, 조도, 간식 소진 이력을 시간순으로 반환합니다.

* **Method**: `GET`
* **Path**: `/api/v1/app/telemetry/history`
* **Query Parameters**:
  * `device_id` (string, 필수): `dogmate-rpi3b-01`
  * `limit` (int, 선택): 조회 포인트 수 (기본값: `30`)
* **cURL Example**:
  ```bash
  curl -X GET "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/telemetry/history?device_id=dogmate-rpi3b-01&limit=30"
  ```
* **Success Response (`200 OK`)**:
  ```json
  [
    {
      "timestamp": "2026-09-15T04:00:00.000000+00:00",
      "temperature": 23.8,
      "humidity": 51.0,
      "light_level": 320,
      "treat_percent": 90
    },
    {
      "timestamp": "2026-09-15T04:30:00.000000+00:00",
      "temperature": 24.5,
      "humidity": 53.0,
      "light_level": 340,
      "treat_percent": 80
    }
  ]
  ```
  *(과거부터 최신순으로 정렬되어 반환되므로 X축 타임스탬프, Y축 수치로 바로 매핑 가능)*

---

## 🔔 3. 모바일 푸시 알림 (Firebase FCM) 규격

라즈베리파이 엣지 AI가 이상 짖음 또는 현관문 배회를 감지하면 클라우드 서버가 FCM 토픽으로 푸시 메시지를 즉시 브로드캐스팅합니다.

* **FCM Topic Name**: `dogmate_dogmate_rpi3b_01`
* **FCM Payload Schema**:
  ```json
  {
    "notification": {
      "title": "🚨 [멍메이트 경보] 반려견 이상 짖음 감지!",
      "body": "소음 84dB (AI 신뢰도 91%). 현장 사진을 확인하세요.",
      "image": "https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/photos/events/..."
    },
    "data": {
      "type": "BARK_ALERT",
      "device_id": "dogmate-rpi3b-01",
      "sound_db": "84",
      "confidence": "0.91",
      "image_url": "/api/v1/app/photos/events/..."
    }
  }
  ```
* **클라이언트 처리 요건**:
  * 앱 시작 시 `dogmate_dogmate_rpi3b_01` 토픽을 구독합니다.
  * 푸시 클릭 시 `data.image_url` 또는 `data.sound_db`를 바탕으로 **이상행동 상세/사진 모달**로 바로 딥링크 이동합니다.

---

## ⚠️ 4. HTTP 에러 응답 규격

* **`400 Bad Request`**: 필수 파라미터(예: `device_id`) 누락 또는 유효하지 않은 요청 포맷
  ```json
  {"error": "device_id는 필수 항목입니다."}
  ```
* **`404 Not Found`**: 등록되지 않은 디바이스 ID 또는 존재하지 않는 사진 파일 경로
  ```json
  {"error": "등록되지 않은 디바이스입니다."}
  ```
* **`500 Internal Server Error`**: 데이터베이스 통신 지연 등 서버 내부 오류
  ```json
  {"error": "상세 오류 메시지"}
  ```
