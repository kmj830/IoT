import os
import contextlib
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

@contextlib.contextmanager
def get_db():
    """
    Supabase PostgreSQL 데이터베이스 연결 컨텍스트 매니저
    트랜잭션 자동 커밋 및 롤백 지원, RealDictCursor(딕셔너리 반환) 기본 적용
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def check_db_health():
    """DB 연결 상태 확인"""
    try:
        with get_db() as cur:
            cur.execute("SELECT 1 AS alive;")
            row = cur.fetchone()
            return row is not None and row["alive"] == 1
    except Exception as e:
        print(f"[DB HealthCheck Error] {e}")
        return False
