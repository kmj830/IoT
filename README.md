# 🌐 IoT 기초설계 팀 프로젝트

> 국립금오공과대학교 컴퓨터공학전공 2026학년도 2학기 **IoT기초설계** (담당: 손기봉 교수님)  
> 라즈베리파이와 각종 센서 및 액추에이터를 활용한 IoT 시스템 구축 및 Flask 웹 연동 프로젝트

---

## 👥 팀원 소개 (Team)

| 이름 | 역할 | 담당 업무 |
| :--- | :--- | :--- |
| **김민중** | 팀원 | 하드웨어 센서/액추에이터 제어, 시스템 설계 |
| **김영재** | 팀원 | Flask 웹 연동 및 대시보드 구현, 시스템 설계 |

*(※ 구체적인 역할 및 주제 선정에 따라 업무 내용을 업데이트해 주세요.)*

---

## 🛠️ 기술 스택 (Tech Stack)

* **Language**: Python 3.x
* **Hardware**: Raspberry Pi, GrovePi+, 센서 및 액추에이터 모듈
* **Web**: Flask, HTML/CSS, JavaScript
* **Tools**: Git, GitHub, PyCharm / VS Code

---

## 📂 프로젝트 구조 (Directory Structure)

```text
IoT/
├── .github/
│   └── pull_request_template.md  # PR 템플릿
├── hardware/                     # 라즈베리파이 하드웨어 제어 모듈
│   ├── sensors/                  # 센서 데이터 수집 스크립트 (조도, 온습도 등)
│   └── actuators/                # 액추에이터 제어 스크립트 (LED, 부저, 서보모터 등)
├── web/                          # Flask 웹 연동 애플리케이션 (11주차~)
│   ├── app.py                    # 웹 서버 메인 실행 파일
│   ├── static/                   # CSS, JS 등 정적 자원
│   └── templates/                # HTML 템플릿 (대시보드 등)
├── docs/                         # 회로도, 설계 계획서, 발표 자료 등 문서
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔌 하드웨어 핀 맵 (GPIO / GrovePi+ Pin Map)

> 💡 센서 및 액추에이터 연결 시 충돌을 방지하기 위해 핀 번호를 기록합니다.

| 구분 | 모듈명 | 포트 / 핀 번호 | 용도 및 설명 |
| :--- | :--- | :--- | :--- |
| **센서** | 조도 센서 (Light Sensor) | A0 | 주변 밝기 측정 |
| **센서** | 온습도 센서 (DHT11) | D4 | 온도 및 습도 데이터 수집 |
| **액추에이터** | LED | D3 | 상태 표시등 점멸 제어 |
| **액추에이터** | 부저 (Buzzer) | D8 | 경보음 출력 |

*(※ 실제 사용하는 센서와 핀에 맞춰 수정해 주세요.)*

---

## 🚀 시작 가이드 (Getting Started)

### 1. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate

# 가상환경 활성화 (Windows)
# .venv\Scripts\activate
```

### 2. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. Flask 웹 서버 실행 (11주차 이후)
```bash
cd web
python3 app.py
```
브라우저에서 `http://localhost:5000` (또는 `http://<라즈베리파이-IP>:5000`) 접속

---

## 🤝 협업 룰 (Git & GitHub Convention)

### 1. 브랜치 전략
* `main`: 안정적인 최종 동작 코드만 유지
* `feature/{기능명}`: 개인 작업 브랜치
  * 예: `feature/dht-sensor`, `feature/web-dashboard`, `feature/buzzer-control`
* 기능 개발 완료 시 `main` 브랜치로 **Pull Request(PR)** 생성 및 팀원 상호 리뷰 후 머지

### 2. 커밋 메시지 컨벤션
* `feat`: 새로운 기능 추가 (센서 드라이버, 웹 페이지 등)
* `fix`: 버그 및 오작동 수정
* `docs`: 문서 작성 및 수정 (README, 회로도 등)
* `refactor`: 코드 리팩토링 및 구조 개선
* `chore`: 빌드 업무 수정, 패키지 매니저 설정 등
