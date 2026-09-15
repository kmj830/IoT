# Google Cloud Run을 위한 최적화 경량 파이썬 베이스 이미지
FROM python:3.11-slim

# 파이썬 출력 버퍼링 비활성화 (실시간 로그 확인용)
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 빌드 의존성 최소 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 의존성 파일 복사 및 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 전체 복사 (.dockerignore에 정의된 파일 제외)
COPY . .

# Google Cloud Run 포트 바인딩 및 Gunicorn 프로덕션 웹서버 실행
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "web.app:app"
