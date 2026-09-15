import os
import datetime
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "dogmate-0830")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "dogmate-0830")

_client = None

def get_storage_client():
    global _client
    if _client is not None:
        return _client
    
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        if not os.path.isabs(cred_path):
            cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cred_path)
        if os.path.exists(cred_path):
            _client = storage.Client.from_service_account_json(cred_path)
    if _client is None:
        # GCP Cloud Run 환경에서는 서비스 계정 ADC(기본 자격 증명)로 자동 인증
        _client = storage.Client(project=GCP_PROJECT_ID)
    
    return _client

def upload_bytes_to_gcs(data: bytes, destination_blob_name: str, content_type: str = "image/jpeg") -> str:
    """
    바이트 데이터를 GCS 버킷에 업로드하고 blob 경로를 반환합니다.
    """
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(data, content_type=content_type)
    return destination_blob_name

def generate_signed_url(blob_name: str, expiration_minutes: int = 15) -> str:
    """
    비공개 GCS 오브젝트에 안전하게 임시 접근할 수 있는 v4 서명된 URL(Signed URL)을 생성합니다.
    """
    if not blob_name:
        return ""
    if blob_name.startswith("http://") or blob_name.startswith("https://"):
        return blob_name
    
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    
    try:
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="GET"
        )
        return url
    except Exception as e:
        print(f"[GCS Signed URL Error] {e}")
        # 서명 생성 실패 시 공용 URL 반환 폴백
        return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"

def check_storage_health() -> bool:
    """GCS 버킷 오브젝트 접근 권한 확인 (Storage Object Admin 호환)"""
    try:
        client = get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        # Storage Object Admin 권한(storage.objects.list)으로 1건만 조회 테스트
        _ = list(client.list_blobs(bucket, max_results=1))
        return True
    except Exception as e:
        print(f"[GCS HealthCheck Error] {e}")
        return False
