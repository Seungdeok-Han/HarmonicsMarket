# Harmonics Market

악기 중고거래가 중심인 웹 앱입니다. 브랜드·모델·상태 정보와 판매자 문의 흐름을 한곳에 모으고, 커뮤니티·AI 연습 도구는 부가 기능으로 둡니다.

> Portfolio project — Flask / SQLAlchemy / Socket.IO

## 핵심 가치

중고 악기 거래에서 자주 끊기는 **매물 파악 → 판매자 신뢰 확인 → 문의** 흐름을 웹 한 흐름으로 연결합니다.

1. 브랜드·모델·상태·시세로 매물을 좁힌다  
2. 판매자 판매중/완료 건수를 보고  
3. 해당 매물 맥락이 붙은 메시지로 바로 문의한다

## 주요 기능

| 영역 | 내용 |
|------|------|
| **중고 거래 (Core)** | 판매글 CRUD, 필터/검색, 다중 이미지, 거래 상태, 조회수·좋아요, YouTube 사운드 샘플 |
| **신뢰·문의** | 판매자 프로필 요약, 매물 연동 1:1 메시지, Socket.IO 실시간 채팅 |
| **커뮤니티** | 피드·댓글·좋아요·팔로우·알림 (DB 저장) |
| **연습 도구** | Gemini 기반 연습 추천, 진행도·연습 일지 (부가 메뉴) |

## 기술 스택

- **Backend:** Python, Flask, Flask-Login, Flask-WTF (CSRF), Flask-Migrate, Flask-SocketIO
- **ORM / DB:** SQLAlchemy, SQLite (개발), Alembic
- **Frontend:** Jinja2, Bootstrap 5, Vanilla JS, Chart.js
- **External:** YouTube Data API, Google Gemini API

## 프로젝트 구조

```
app/
  routes/           # Blueprint 모듈 (marketplace/sns/practice/sockets…)
  services/         # 알림·커뮤니티 직렬화/시드
  utils/            # 업로드·상대시간
  models.py         # 도메인 모델
  templates/        # Jinja UI
  static/           # CSS/JS/업로드
migrations/         # Alembic
data/sns_posts.json # 레거시 시드 (최초 1회 DB로 import)
```

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env        # 없으면 아래 변수로 .env 생성
flask db upgrade
flask run
# 또는: python run.py
```

`.env` 예시:

```env
FLASK_APP=run.py
SECRET_KEY=change-me
YOUTUBE_API_KEY=
GEMINI_API_KEY=
```

API 키가 없어도 거래·커뮤니티·메시지는 동작합니다. YouTube/Gemini만 비활성됩니다.

## 설계 메모 (포트폴리오)

- 커뮤니티는 파일 JSON → **관계형 DB**로 이전했고, 프론트 JSON shape은 유지했습니다.
- 라우트는 `main` Blueprint endpoint를 유지한 채 **모듈로 분리**해 템플릿 churn을 줄였습니다.
- 업로드는 UUID 파일명, 폼/AJAX는 CSRF 토큰을 사용합니다.
- 좋아요·팔로우 등에 DB 유니크 제약을 두어 중복을 막습니다.

## 라이선스

MIT

## 개발

Han Seung Deok · gkstmdejr99@gmail.com
