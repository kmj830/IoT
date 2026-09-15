# 📱 멍메이트(DogMate) 모바일 프론트엔드 연동 & 개발 가이드 (For Frontend AI)
> **대상**: 다른 프로젝트 폴더에서 모바일 앱(Flutter, React Native, Swift, Kotlin 등)을 구현할 **프론트엔드 AI 에이전트 및 개발자**  
> **과목**: 국립금오공과대학교 2026-2 IoT기초설계 (팀원: 김민중, 김영재)  
> **백엔드 배포 상태**: Google Cloud Run 프로덕션 가동 중 (검증 완료 100% PASS)  
> **문서 버전**: v1.0

---

## 🎯 1. 프로젝트 개요 & 프론트엔드 미션

**멍메이트(DogMate)**는 1인 가구 분리불안 반려견을 위한 **원격 인터랙티브 IoT 케어 스마트홈 시스템**입니다.  
라즈베리파이 3B 엣지 디바이스가 집안에서 센서와 AI로 반려견을 감시하고, 클라우드(Cloud Run + Supabase + GCS)를 거쳐 **보호자의 스마트폰 모바일 앱**으로 연결됩니다.

### 📱 프론트엔드 앱의 4대 핵심 화면
1. **🏠 메인 홈 대시보드**: 키트 온/오프라인 상태, 실내 온·습도·조도 카드, **간식 잔여량(%) 게이지**, 원클릭 **[간식 주기]** 버튼
2. **🎙️ Push-to-Talk 음성 전송 화면**: 마이크 버튼을 길게 누르고 *"뽀삐야~"* 말하면 음성 파일이 키트 스피커로 원격 송출
3. **🚨 이상행동 피드 & 사진 갤러리**: YAMNet AI가 감지한 짖음 소음(dB) 및 현관문 배회(ROI) 기록 타임라인 + 캡처 사진 풀스크린 모달 뷰어
4. **📊 24시간 환경 통계 차트**: 실내 온습도 변화 및 간식 소진 추이를 보여주는 시계열 꺾은선 그래프

---

## 🌐 2. 서버 접속 환경 & 기본 정보

* **프로덕션 API Base URL**:  
  `https://dogmate-backend-1089229092493.us-central1.run.app`
* **로컬 개발용 API Base URL**:  
  `http://localhost:5001` (또는 로컬 Wi-Fi IP)
* **대화형 Swagger API 문서 (UI)**:  
  `https://dogmate-backend-1089229092493.us-central1.run.app/docs`
* **OpenAPI 3.0 스키마 (JSON)**:  
  `https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/swagger.json`
* **기본 테스트 디바이스 ID**: `dogmate-rpi3b-01`
* **CORS 설정**: 전 엔드포인트 `CORS(*)` 허용 완료 (웹/에뮬레이터/실기기 통신 차단 없음)

---

## 🔌 3. 프론트엔드 연동 REST API 상세 명세

### ① 🏠 실시간 홈 대시보드 상태 조회
- **엔드포인트**: `GET /api/v1/app/status`
- **Query Parameters**:
  - `device_id` (String, 필수): 기본값 `dogmate-rpi3b-01`
- **성공 응답 (`200 OK`)**:
  ```json
  {
    "device_id": "dogmate-rpi3b-01",
    "name": "우리집 멍메이트",
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

---

### ② 🍖 원격 간식 급여 요청
- **엔드포인트**: `POST /api/v1/app/feed`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "device_id": "dogmate-rpi3b-01",
    "amount": 1
  }
  ```
- **성공 응답 (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "간식 투출 명령이 디바이스(dogmate-rpi3b-01)로 전송 대기열에 등록되었습니다.",
    "command_id": 3
  }
  ```
  *(호출 즉시 라즈베리파이 서보모터가 180도 회전하여 간식을 투출하며, 잠시 후 대시보드 `treat_percent`가 5% 차감됩니다.)*

---

### ③ 🎙️ Push-to-Talk 보호자 음성 메시지 전송
- **엔드포인트**: `POST /api/v1/app/voice`
- **Headers**: `Content-Type: multipart/form-data`
- **Request FormData**:
  - `device_id` (Text): `dogmate-rpi3b-01`
  - `voice` (File): 녹음된 오디오 파일 (`.wav` 권장, `.m4a` 지원)
- **성공 응답 (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "음성 파일이 안전하게 업로드되었으며 재생 명령이 대기열에 등록되었습니다.",
    "command_id": 4,
    "voice_url": "/api/v1/app/photos/voices/dogmate-rpi3b-01/ca59e8.wav"
  }
  ```
  *(서버가 음성을 GCS에 저장 후 디바이스로 전달하여 키트 스피커로 즉시 재생됩니다.)*

---

### ④ 🚨 이상행동(짖음/현관 배회) 기록 목록 조회
- **엔드포인트**: `GET /api/v1/app/events`
- **Query Parameters**:
  - `device_id` (String, 필수): `dogmate-rpi3b-01`
  - `limit` (Int, 선택): 조회할 개수 (기본값 `10`)
- **성공 응답 (`200 OK`)**:
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

---

### ⑤ 🖼️ 비공개 GCS 보안 사진 스트리밍
- **엔드포인트**: `GET /api/v1/app/photos/<이미지경로>`
- **동작 방식**: 
  - 이벤트 목록에서 반환된 `image_url`(예: `/api/v1/app/photos/events/...jpg`)을 Base URL 뒤에 그대로 붙여 호출합니다.
  - 예: `https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/app/photos/events/dogmate-rpi3b-01/bark_4.jpg`
- **응답**: `image/jpeg` 바이너리 직접 반환 (모바일 앱의 `Image.network()`에 넣으면 바로 렌더링됨)

---

### ⑥ 📊 24시간 센서 시계열 통계 (차트용)
- **엔드포인트**: `GET /api/v1/app/telemetry/history`
- **Query Parameters**:
  - `device_id` (String, 필수): `dogmate-rpi3b-01`
  - `limit` (Int, 선택): 기본값 `30`
- **성공 응답 (`200 OK`)**:
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
  *(과거부터 최신순으로 정렬되어 반환되므로 차트 라이브러리 X축에 그대로 바인딩 가능)*

---

## 🔔 4. 스마트폰 긴급 푸시 알림 (Firebase FCM) 연동

반려견 이상 짖음이나 현관문 배회가 감지되면 서버가 자동으로 FCM 토픽으로 푸시를 발송합니다.

* **FCM 구독 토픽명**: `dogmate_dogmate_rpi3b_01`
* **모바일 앱 등록 코드 (Flutter 예시)**:
  ```dart
  import 'package:firebase_messaging/firebase_messaging.dart';

  void setupFCM() async {
    FirebaseMessaging messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);

    // 멍메이트 키트 토픽 구독
    await messaging.subscribeToTopic('dogmate_dogmate_rpi3b_01');

    // 포그라운드 메시지 수신 핸들러
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print("🚨 푸시 수신: ${message.notification?.title} - ${message.notification?.body}");
      // message.data['image_url'] 로 사진 확인 가능
    });
  }
  ```

---

## 💻 5. Flutter / React Native 핵심 API 클라이언트 예제

### 🔹 Flutter (Dart / Dio)
```dart
import 'package:dio/dio.dart';

class DogMateApi {
  static const String baseUrl = 'https://dogmate-backend-1089229092493.us-central1.run.app';
  static const String deviceId = 'dogmate-rpi3b-01';
  final Dio _dio = Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 8)));

  // 1. 대시보드 상태 조회
  Future<Map<String, dynamic>> getStatus() async {
    final res = await _dio.get('/api/v1/app/status', queryParameters: {'device_id': deviceId});
    return res.data;
  }

  // 2. 간식 주기
  Future<bool> feedTreat({int amount = 1}) async {
    final res = await _dio.post('/api/v1/app/feed', data: {'device_id': deviceId, 'amount': amount});
    return res.data['success'] == true;
  }

  // 3. 음성 파일 전송 (Push-to-Talk)
  Future<bool> sendVoice(String filePath) async {
    FormData formData = FormData.fromMap({
      'device_id': deviceId,
      'voice': await MultipartFile.fromFile(filePath, filename: 'voice.wav'),
    });
    final res = await _dio.post('/api/v1/app/voice', data: formData);
    return res.data['success'] == true;
  }

  // 4. 이미지 URL 생성 헬퍼
  String getFullImageUrl(String relativePath) {
    if (relativePath.startsWith('http')) return relativePath;
    return '$baseUrl$relativePath';
  }
}
```

---

## 🧪 6. 개발 중 하드웨어 실시간 연동 테스트 방법

프론트엔드 개발 시 라즈베리파이 실물이 없어도, IoT 백엔드 저장소의 시뮬레이터를 켜두면 **앱 화면에서 [간식 주기]를 누를 때마다 터미널에서 실시간으로 서보모터가 반응**하는 것을 보면서 개발할 수 있습니다:

```bash
cd /Users/minjung/Dev/IoT
.venv/bin/python hardware/simulate.py
# 7번(연속 가동 모드) 선택
```

프론트엔드 AI 에이전트는 위 명세서를 바탕으로 즉시 화면 구현 및 API 연동을 진행하시면 됩니다! 🚀
