import os
import sys
import uuid
import base64
from pathlib import Path
from datetime import datetime, timezone

# 프로젝트 루트 경로를 sys.path에 추가하여 어디서 실행하든 모듈 임포트 가능하도록 보장
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, render_template, request, jsonify, Response
from flask_restx import Api, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage
from dotenv import load_dotenv

from web.db import get_db, check_db_health
from web.storage import upload_bytes_to_gcs, generate_signed_url, check_storage_health
from web.fcm import send_bark_alert

load_dotenv()

app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = False  # X-Fields 헤더 비활성화
app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'

# Swagger UI API 설정 (/docs)
api = Api(
    app,
    version="1.0.0",
    title="🐶 멍메이트(DogMate) IoT Cloud API",
    description=(
        "## 국립금오공과대학교 2026-2 IoT기초설계\n"
        "### 반려견 분리불안 완화 및 인터랙티브 원격 케어 IoT 시스템\n\n"
        "- **팀원**: 김민중, 김영재\n"
        "- **아키텍처**: Google Cloud Run + Supabase PostgreSQL 15 + GCS + Firebase FCM ($0/mo Always Free)\n"
        "- **문서 설명**: 라즈베리파이(Edge)와 보호자 모바일 앱 간의 REST API 및 엔드포인트 명세입니다."
    ),
    doc="/docs",
    prefix="/api/v1"
)

# 네임스페이스 정의
ns_health = api.namespace('health', description='클라우드 인프라 헬스체크')
ns_devices = api.namespace('devices', description='라즈베리파이 엣지 디바이스 통신 API')
ns_app = api.namespace('app', description='보호자 모바일 앱 및 웹 대시보드 API')

# ==========================================
# Swagger 데이터 모델(DTO) 정의
# ==========================================

# 1. 텔레메트리 모델
telemetry_model = api.model('TelemetryRequest', {
    'device_id': fields.String(required=True, description='디바이스 고유 식별자', example='dogmate-rpi3b-01'),
    'temperature': fields.Float(description='온도 (℃)', example=23.8),
    'humidity': fields.Float(description='습도 (%)', example=52.4),
    'light_level': fields.Integer(description='조도 센서값 (Lux)', example=320),
    'treat_percent': fields.Integer(description='간식 잔여량 (%)', example=85)
})

# 2. 하트비트 모델
heartbeat_model = api.model('HeartbeatRequest', {
    'device_id': fields.String(required=True, description='디바이스 고유 식별자', example='dogmate-rpi3b-01')
})

# 3. 짖음 이벤트 JSON 모델 (Base64 지원)
bark_event_json_model = api.model('BarkEventJsonRequest', {
    'device_id': fields.String(required=True, description='디바이스 고유 식별자', example='dogmate-rpi3b-01'),
    'sound_db': fields.Integer(required=True, description='감지된 음향 데시벨(dB)', example=78),
    'confidence': fields.Float(required=True, description='YAMNet 짖음 AI 신뢰도(0.0~1.0)', example=0.89),
    'image_base64': fields.String(description='카메라 캡처 JPEG Base64 인코딩 문자열 (선택)', example='')
})

# 4. 명령 확인(ACK) 모델
ack_model = api.model('CommandAckRequest', {
    'command_id': fields.Integer(required=True, description='명령 ID', example=1),
    'device_id': fields.String(required=True, description='디바이스 고유 식별자', example='dogmate-rpi3b-01'),
    'status': fields.String(required=True, description='실행 상태 (completed / failed)', example='completed')
})

# 5. 간식 급여 요청 모델
feed_request_model = api.model('FeedRequest', {
    'device_id': fields.String(required=True, description='디바이스 고유 식별자', example='dogmate-rpi3b-01'),
    'amount': fields.Integer(description='간식 투출 횟수/양', default=1, example=1)
})


# ==========================================
# 1. HealthCheck Endpoints
# ==========================================
@ns_health.route('')
class HealthCheck(Resource):
    @ns_health.doc(summary='클라우드 백엔드 및 의존 서비스 상태 점검')
    def get(self):
        """DB(Supabase) 및 오브젝트 스토리지(GCS) 연동 상태를 확인합니다."""
        db_ok = check_db_health()
        storage_ok = check_storage_health()
        
        status = "healthy" if (db_ok and storage_ok) else "degraded"
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "supabase_postgresql": "connected" if db_ok else "unreachable",
                "google_cloud_storage": "connected" if storage_ok else "unreachable"
            },
            "environment": os.getenv("FLASK_ENV", "production")
        }, 200 if status == "healthy" else 503


@app.route('/health')
def plain_health():
    """GCP Cloud Run 및 모니터링용 루트 헬스체크 엔드포인트"""
    return jsonify({"status": "ok", "service": "dogmate-cloud-api"}), 200


# ==========================================
# 2. Devices Endpoints (라즈베리파이 ➔ GCP)
# ==========================================
@ns_devices.route('/telemetry')
class DeviceTelemetry(Resource):
    @ns_devices.expect(telemetry_model, validate=True)
    @ns_devices.doc(summary='라즈베리파이 환경 센서 시계열 데이터 업로드')
    def post(self):
        """
        라즈베리파이에서 수집한 온/습도, 조도, 간식 잔여량 데이터를 Supabase DB에 적재하고
        디바이스의 온라인 상태와 하트비트를 자동 갱신합니다.
        """
        data = request.json
        device_id = data.get('device_id')
        temp = data.get('temperature')
        hum = data.get('humidity')
        light = data.get('light_level')
        treat = data.get('treat_percent')
        
        try:
            with get_db() as cur:
                # 1. 디바이스 하트비트 및 온라인 상태 갱신
                cur.execute("""
                    INSERT INTO devices (device_id, name, owner_email, status, last_heartbeat)
                    VALUES (%s, '우리집 멍메이트', 'owner@dogmate.local', 'online', NOW())
                    ON CONFLICT (device_id) DO UPDATE
                    SET status = 'online', last_heartbeat = NOW();
                """, (device_id,))
                
                # 2. 텔레메트리 시계열 기록
                cur.execute("""
                    INSERT INTO sensor_telemetry (device_id, temperature, humidity, light_level, treat_percent)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, timestamp;
                """, (device_id, temp, hum, light, treat))
                row = cur.fetchone()
                
            return {
                "status": "recorded",
                "telemetry_id": row["id"],
                "device_id": device_id,
                "recorded_at": row["timestamp"].isoformat()
            }, 201
        except Exception as e:
            return {"error": str(e)}, 500


@ns_devices.route('/heartbeat')
class DeviceHeartbeat(Resource):
    @ns_devices.expect(heartbeat_model, validate=True)
    @ns_devices.doc(summary='라즈베리파이 연결 유지 하트비트')
    def post(self):
        """디바이스 생존 신호를 수신하여 last_heartbeat 및 status를 'online'으로 갱신합니다."""
        device_id = request.json.get('device_id')
        try:
            with get_db() as cur:
                cur.execute("""
                    UPDATE devices
                    SET status = 'online', last_heartbeat = NOW()
                    WHERE device_id = %s;
                """, (device_id,))
            return {"status": "alive", "device_id": device_id}, 200
        except Exception as e:
            return {"error": str(e)}, 500


bark_file_parser = reqparse.RequestParser()
bark_file_parser.add_argument('device_id', type=str, required=True, location='form', help='디바이스 ID')
bark_file_parser.add_argument('sound_db', type=int, required=True, location='form', help='음향 dB')
bark_file_parser.add_argument('confidence', type=float, required=True, location='form', help='AI 신뢰도')
bark_file_parser.add_argument('image', type=FileStorage, location='files', required=False, help='현장 캡처 사진 파일')

@ns_devices.route('/events/bark')
class DeviceBarkEvent(Resource):
    @ns_devices.expect(bark_file_parser)
    @ns_devices.doc(summary='이상 짖음 감지 시 사진 및 AI 분석 결과 리포트')
    def post(self):
        """
        라즈베리파이 YAMNet AI가 짖음을 감지했을 때 캡처한 현장 사진을
        GCS 버킷(dogmate-0830)에 업로드하고, Supabase DB 기록 및 보호자 푸시(FCM)를 발송합니다.
        (multipart/form-data 또는 JSON Base64 모두 지원)
        """
        device_id = request.form.get('device_id')
        sound_db = request.form.get('sound_db', type=int)
        confidence = request.form.get('confidence', type=float)
        image_file = request.files.get('image')
        
        # JSON 요청 폴백 지원 (Swagger 편리한 테스트를 위해)
        if not device_id and request.is_json:
            data = request.json or {}
            device_id = data.get('device_id')
            sound_db = data.get('sound_db', 70)
            confidence = data.get('confidence', 0.85)
            img_b64 = data.get('image_base64', '')
            image_bytes = base64.b64decode(img_b64) if img_b64 else b"MOCK_IMAGE_DATA"
        elif image_file:
            image_bytes = image_file.read()
        else:
            image_bytes = b"EMPTY_IMAGE"

        if not device_id:
            return {"error": "device_id는 필수 항목입니다."}, 400

        # GCS 파일명 생성 및 업로드
        filename = f"events/{device_id}/{uuid.uuid4().hex}.jpg"
        try:
            upload_bytes_to_gcs(image_bytes, filename, content_type="image/jpeg")
            signed_url = generate_signed_url(filename, expiration_minutes=60)
            
            with get_db() as cur:
                cur.execute("""
                    INSERT INTO bark_events (device_id, sound_db, confidence, gcs_image_url)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, timestamp;
                """, (device_id, sound_db, confidence, filename))
                row = cur.fetchone()
            
            # 보호자 스마트폰으로 실시간 긴급 푸시 알림 발송
            send_bark_alert(device_id, sound_db or 70, confidence or 0.8, signed_url)
            
            return {
                "event_id": row["id"],
                "status": "alert_processed",
                "device_id": device_id,
                "sound_db": sound_db,
                "confidence": confidence,
                "gcs_blob": filename,
                "view_url": signed_url,
                "created_at": row["timestamp"].isoformat()
            }, 201
        except Exception as e:
            return {"error": str(e)}, 500


@ns_devices.route('/commands/pending')
class DevicePendingCommands(Resource):
    @ns_devices.param('device_id', '조회할 디바이스 ID', required=True, default='dogmate-rpi3b-01')
    @ns_devices.doc(summary='라즈베리파이가 실행할 대기 중인 원격 명령 조회')
    def get(self):
        """라즈베리파이가 부팅 또는 폴링 시 전달받을 미실행 명령 목록을 조회하고 상태를 'sent'로 변경합니다."""
        device_id = request.args.get('device_id')
        if not device_id:
            return {"error": "device_id 파라미터가 필요합니다."}, 400
        
        try:
            with get_db() as cur:
                cur.execute("""
                    SELECT id, command_type, payload, created_at
                    FROM device_commands
                    WHERE device_id = %s AND status = 'pending'
                    ORDER BY id ASC;
                """, (device_id,))
                commands = cur.fetchall()
                
                if commands:
                    cmd_ids = [c["id"] for c in commands]
                    cur.execute("""
                        UPDATE device_commands
                        SET status = 'sent'
                        WHERE id = ANY(%s);
                    """, (cmd_ids,))
            
            return [{
                "id": c["id"],
                "command_type": c["command_type"],
                "payload": c["payload"],
                "created_at": c["created_at"].isoformat()
            } for c in commands], 200
        except Exception as e:
            return {"error": str(e)}, 500


@ns_devices.route('/commands/ack')
class DeviceCommandAck(Resource):
    @ns_devices.expect(ack_model, validate=True)
    @ns_devices.doc(summary='라즈베리파이 명령 실행 완료 보고 (ACK)')
    def post(self):
        """서보모터 간식 투출이나 스피커 음성 재생 후 실행 결과를 클라우드에 최종 보고합니다."""
        data = request.json
        cmd_id = data.get('command_id')
        device_id = data.get('device_id')
        status = data.get('status', 'completed')
        
        try:
            with get_db() as cur:
                cur.execute("""
                    UPDATE device_commands
                    SET status = %s, executed_at = NOW()
                    WHERE id = %s AND device_id = %s;
                """, (status, cmd_id, device_id))
            return {"status": "acknowledged", "command_id": cmd_id}, 200
        except Exception as e:
            return {"error": str(e)}, 500


# ==========================================
# 3. Client/App Endpoints (보호자 앱 ➔ GCP)
# ==========================================
@ns_app.route('/status')
class AppStatus(Resource):
    @ns_app.param('device_id', '조회할 디바이스 ID', required=True, default='dogmate-rpi3b-01')
    @ns_app.doc(summary='보호자 대시보드 실시간 통합 상태 조회')
    def get(self):
        """디바이스 온라인 여부, 최신 온/습도, 조도, 간식 잔여량, 최근 짖음 발생 시각을 원클릭 조회합니다."""
        device_id = request.args.get('device_id', 'dogmate-rpi3b-01')
        try:
            with get_db() as cur:
                # 디바이스 정보
                cur.execute("""
                    SELECT device_id, name, status, last_heartbeat
                    FROM devices WHERE device_id = %s;
                """, (device_id,))
                device = cur.fetchone()
                
                # 최신 센서 데이터
                cur.execute("""
                    SELECT temperature, humidity, light_level, treat_percent, timestamp
                    FROM sensor_telemetry
                    WHERE device_id = %s
                    ORDER BY timestamp DESC LIMIT 1;
                """, (device_id,))
                telemetry = cur.fetchone()
                
                # 최신 짖음 이벤트
                cur.execute("""
                    SELECT timestamp, sound_db, confidence, gcs_image_url
                    FROM bark_events
                    WHERE device_id = %s
                    ORDER BY timestamp DESC LIMIT 1;
                """, (device_id,))
                bark = cur.fetchone()
            
            if not device:
                return {"error": "등록되지 않은 디바이스입니다."}, 404
            
            last_bark_info = None
            if bark:
                last_bark_info = {
                    "timestamp": bark["timestamp"].isoformat(),
                    "sound_db": bark["sound_db"],
                    "confidence": bark["confidence"],
                    "image_url": generate_signed_url(bark["gcs_image_url"])
                }
            
            return {
                "device_id": device["device_id"],
                "name": device["name"],
                "online": device["status"] == 'online',
                "last_heartbeat": device["last_heartbeat"].isoformat() if device["last_heartbeat"] else None,
                "telemetry": {
                    "temperature": telemetry["temperature"] if telemetry else None,
                    "humidity": telemetry["humidity"] if telemetry else None,
                    "light_level": telemetry["light_level"] if telemetry else None,
                    "treat_percent": telemetry["treat_percent"] if telemetry else None,
                    "measured_at": telemetry["timestamp"].isoformat() if telemetry else None
                } if telemetry else None,
                "latest_bark_event": last_bark_info
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500


@ns_app.route('/feed')
class AppFeed(Resource):
    @ns_app.expect(feed_request_model, validate=True)
    @ns_app.doc(summary='스마트폰 원격 수동 간식 급여 요청')
    def post(self):
        """보호자가 앱에서 [간식 주기] 클릭 시, 디바이스 명령 큐에 서보 투출 명령을 적재하고 감사 로그를 남깁니다."""
        data = request.json
        device_id = data.get('device_id')
        amount = data.get('amount', 1)
        
        try:
            with get_db() as cur:
                # 1. 명령 큐 적재
                cur.execute("""
                    INSERT INTO device_commands (device_id, command_type, payload, status)
                    VALUES (%s, 'FEED_TREAT', %s::jsonb, 'pending')
                    RETURNING id;
                """, (device_id, f'{{"amount": {amount}}}'))
                cmd_row = cur.fetchone()
                
                # 2. 간식 로그 적재
                cur.execute("""
                    INSERT INTO feed_logs (device_id, trigger_type, status)
                    VALUES (%s, 'manual', 'requested');
                """, (device_id,))
            
            return {
                "success": True,
                "message": f"간식 투출 명령이 디바이스({device_id})로 전송 대기열에 등록되었습니다.",
                "command_id": cmd_row["id"]
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500


voice_parser = reqparse.RequestParser()
voice_parser.add_argument('device_id', type=str, required=True, location='form', help='디바이스 ID')
voice_parser.add_argument('voice', type=FileStorage, location='files', required=True, help='녹음된 WAV 음성 파일')

@ns_app.route('/voice')
class AppVoice(Resource):
    @ns_app.expect(voice_parser)
    @ns_app.doc(summary='보호자 Push-to-Talk 음성 메시지 전송')
    def post(self):
        """보호자가 녹음한 위로 음성(WAV)을 GCS에 저장하고, 라즈베리파이에 스피커 재생 명령을 하달합니다."""
        device_id = request.form.get('device_id')
        voice_file = request.files.get('voice')
        
        if not device_id or not voice_file:
            return {"error": "device_id와 voice 파일이 모두 필요합니다."}, 400
        
        filename = f"voices/{device_id}/{uuid.uuid4().hex}.wav"
        try:
            upload_bytes_to_gcs(voice_file.read(), filename, content_type="audio/wav")
            voice_url = generate_signed_url(filename, expiration_minutes=30)
            
            with get_db() as cur:
                cur.execute("""
                    INSERT INTO device_commands (device_id, command_type, payload, status)
                    VALUES (%s, 'PLAY_VOICE', %s::jsonb, 'pending')
                    RETURNING id;
                """, (device_id, f'{{"voice_url": "{voice_url}", "blob": "{filename}"}}'))
                cmd_row = cur.fetchone()
            
            return {
                "success": True,
                "message": "음성 파일이 안전하게 업로드되었으며 재생 명령이 대기열에 등록되었습니다.",
                "command_id": cmd_row["id"],
                "voice_url": voice_url
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500


@ns_app.route('/events')
class AppBarkEvents(Resource):
    @ns_app.param('device_id', '조회할 디바이스 ID', required=True, default='dogmate-rpi3b-01')
    @ns_app.param('limit', '조회할 이벤트 개수', default=10)
    @ns_app.doc(summary='최근 이상 짖음 감지 내역 및 사진 목록 조회')
    def get(self):
        """보호자 앱에서 최근 발생한 이상 짖음 기록과 당시 카메라 캡처 사진(서명 URL)을 목록으로 조회합니다."""
        device_id = request.args.get('device_id', 'dogmate-rpi3b-01')
        limit = request.args.get('limit', 10, type=int)
        
        try:
            with get_db() as cur:
                cur.execute("""
                    SELECT id, timestamp, sound_db, confidence, gcs_image_url, is_resolved
                    FROM bark_events
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s;
                """, (device_id, limit))
                rows = cur.fetchall()
            
            events = []
            for r in rows:
                events.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"].isoformat(),
                    "sound_db": r["sound_db"],
                    "confidence": r["confidence"],
                    "image_url": generate_signed_url(r["gcs_image_url"]),
                    "is_resolved": r["is_resolved"]
                })
            return events, 200
        except Exception as e:
            return {"error": str(e)}, 500


@ns_app.route('/telemetry/history')
class AppTelemetryHistory(Resource):
    @ns_app.param('device_id', '조회할 디바이스 ID', required=True, default='dogmate-rpi3b-01')
    @ns_app.param('limit', '조회 개수 (기본 30개)', default=30)
    @ns_app.doc(summary='센서 시계열 히스토리 (차트용)')
    def get(self):
        """모바일 앱/웹 대시보드 그래프 시각화를 위한 최근 온습도/조도/간식 시계열 데이터를 반환합니다."""
        device_id = request.args.get('device_id', 'dogmate-rpi3b-01')
        limit = request.args.get('limit', 30, type=int)
        
        try:
            with get_db() as cur:
                cur.execute("""
                    SELECT timestamp, temperature, humidity, light_level, treat_percent
                    FROM sensor_telemetry
                    WHERE device_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s;
                """, (device_id, limit))
                rows = cur.fetchall()
            
            # 시계열 순(과거 -> 최신) 정렬하여 반환
            history = [{
                "timestamp": r["timestamp"].isoformat(),
                "temperature": r["temperature"],
                "humidity": r["humidity"],
                "light_level": r["light_level"],
                "treat_percent": r["treat_percent"]
            } for r in reversed(rows)]
            return history, 200
        except Exception as e:
            return {"error": str(e)}, 500


# ==========================================
# 4. 웹 메인 대시보드 및 보안 미디어 스트리밍
# ==========================================
@app.route('/api/v1/app/photos/<path:blob_name>')
def stream_photo(blob_name):
    """
    GCS 버킷의 비공개 반려견 캡처 사진을 안전하게 클라이언트로 스트리밍합니다.
    버킷을 퍼블릭으로 노출하지 않고도 브라우저와 모바일 앱에서 즉시 열람 가능합니다.
    """
    try:
        from web.storage import download_blob_bytes
        img_bytes = download_blob_bytes(blob_name)
        return Response(img_bytes, mimetype="image/jpeg", headers={
            "Cache-Control": "public, max-age=3600"
        })
    except Exception as e:
        return jsonify({"error": f"이미지를 불러올 수 없습니다: {str(e)}"}), 404


@app.route('/')
def index():
    """모니터링 웹 대시보드 및 Swagger 안내 메인 페이지"""
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"🐶 [DogMate] API 서버 가동 중: http://0.0.0.0:{port} (Swagger 문서: http://0.0.0.0:{port}/docs)")
    app.run(host='0.0.0.0', port=port, debug=True)
