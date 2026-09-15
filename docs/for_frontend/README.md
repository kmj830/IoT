# 📦 멍메이트(DogMate) 프론트엔드 개발 전달 패키지 (Frontend Handoff Pack)

본 폴더(`docs/for_frontend/`)는 **프론트엔드 개발자 및 프론트엔드 AI 에이전트**가 별도의 백엔드 코드 분석 없이, 바로 클라이언트 애플리케이션(모바일 앱 또는 웹)을 개발할 수 있도록 선별·정리한 공식 핸드오프 문서 모음입니다.

---

## 🌐 1. 서버 접속 기본 정보

* **프로덕션 API 서버 주소**:  
  `https://dogmate-backend-1089229092493.us-central1.run.app`
* **대화형 Swagger API 문서**:  
  [https://dogmate-backend-1089229092493.us-central1.run.app/docs](https://dogmate-backend-1089229092493.us-central1.run.app/docs)
* **OpenAPI 3.0 스키마 (JSON)**:  
  `https://dogmate-backend-1089229092493.us-central1.run.app/api/v1/swagger.json`
* **기본 디바이스 식별자 (Device ID)**: `dogmate-rpi3b-01`
* **CORS 설정**: 전 엔드포인트 `CORS(*)` 허용 완료 (어떤 프레임워크/플랫폼에서 호출하든 교차 출처 차단 없음)

---

## 📁 2. 전달 문서 구성

| 파일명 | 내용 요약 |
| :--- | :--- |
| **[`API_SPECIFICATION.md`](API_SPECIFICATION.md)** | 언어/프레임워크에 종속되지 않는 **순수 RESTful HTTP API 규격서** (엔드포인트, 헤더, JSON 입출력 스키마, FCM 푸시 페이로드, cURL 예제) |
| **[`SERVICE_REQUIREMENTS.md`](SERVICE_REQUIREMENTS.md)** | 멍메이트 서비스의 **UI/UX 기획서 및 4대 핵심 화면 요구사항** (화면 구성, 유저 인터랙션 흐름, 실시간 피드백 로직) |

---

## 🚀 3. 프론트엔드 AI 에이전트 작업 프롬프트 추천

다른 프로젝트 폴더에서 프론트엔드 AI 에이전트에게 작업을 지시할 때 아래와 같이 전달하시면 가장 빠르고 정확하게 개발을 진행할 수 있습니다:

```text
우리는 멍메이트(DogMate)라는 반려동물 분리불안 완화 및 원격 케어 서비스의 클라이언트 애플리케이션을 개발하고 있습니다.
백엔드 API 및 서비스 기획 문서는 'docs/for_frontend/' 폴더에 정리되어 있습니다:
- 'docs/for_frontend/SERVICE_REQUIREMENTS.md'의 화면 기획과 유저 플로우를 참고하여 UI를 구성해주세요.
- 'docs/for_frontend/API_SPECIFICATION.md'의 REST API 규격에 맞춰 서버와 통신하는 클라이언트를 구현해주세요.
서버는 Google Cloud Run(https://dogmate-backend-1089229092493.us-central1.run.app)에 배포되어 즉시 통신이 가능한 상태입니다.
```
