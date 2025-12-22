# 🎸 하모닉스 마켓 (Harmonics Market)

악기 중고거래 및 연주 커뮤니티 플랫폼

## 📌 주요 기능

### 🛒 중고 거래
- 악기 판매글 작성/수정/삭제
- 브랜드/장르/형태별 필터링 & 검색
- 여러 이미지 업로드 지원
- 거래 상태 관리 (판매중/예약중/판매완료)
- YouTube 연주 영상 자동 검색
- 조회수 및 좋아요 시스템

### 💬 소셜 기능
- SNS 피드 (무한 스크롤)
- 댓글 및 대댓글
- 좋아요 시스템
- 팔로우/팔로워 관리
- 1:1 메시지
- 실시간 알림

### 🎵 AI 기반 연습 추천
- Google Gemini API를 활용한 맞춤형 연습 추천
- 경력/장르/목표에 따른 곡 & 기술 추천
- 특정 곡 지정 기능
- YouTube 튜토리얼 자동 검색

### 📊 연습 관리
- 추천 내용 저장 및 관리
- 곡/기술별 진행도 트래킹 (미시작/연습중/완료)
- 연습 일지 작성
- 연속 연습일 통계 (스트릭 계산)
- 총 연습 시간 집계

## 🛠️ 기술 스택

### Backend
- **Python 3.x**
- **Flask** - 웹 프레임워크
- **SQLAlchemy** - ORM
- **Flask-Migrate** - 데이터베이스 마이그레이션
- **Flask-Login** - 사용자 인증

### Frontend
- **Bootstrap 5** - UI 프레임워크
- **Jinja2** - 템플릿 엔진
- **JavaScript (Vanilla)** - 동적 기능
- **Chart.js** - 시세 차트 시각화

### APIs
- **YouTube Data API v3** - 영상 검색
- **Google Gemini API** - AI 추천 생성

### Database
- **SQLite** - 개발용 데이터베이스
- **Alembic** - 마이그레이션 관리

## 📁 프로젝트 구조

```
PythonProject4/
├── app/
│   ├── __init__.py           # Flask 앱 초기화
│   ├── models.py             # 데이터베이스 모델 (13개 모델)
│   ├── routes.py             # 메인 라우트 (거래, SNS, 연습 등)
│   ├── routes_auth.py        # 인증 라우트 (로그인/회원가입)
│   ├── user.py               # 사용자 블루프린트
│   ├── static/               # 정적 파일 (CSS, JS, 업로드 이미지)
│   └── templates/            # Jinja2 템플릿
├── migrations/               # Alembic 마이그레이션 파일
├── data/                     # SNS 데이터 (JSON)
├── .vscode/                  # VS Code 설정 (Flask 실행 태스크)
├── config.py                 # 앱 설정
├── run.py                    # 앱 실행 진입점
├── requirements.txt          # 패키지 의존성
├── .env                      # 환경변수 (API 키 등)
└── .gitignore
```

## 🚀 설치 및 실행

### 1. 저장소 클론
```powershell
git clone <repository-url>
cd PythonProject4
```

### 2. 가상환경 생성 및 활성화
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 패키지 설치
```powershell
pip install -r requirements.txt
```

### 4. 환경변수 설정
`.env` 파일을 생성하고 아래 내용을 입력:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
YOUTUBE_API_KEY=your-youtube-api-key
GEMINI_API_KEY=your-gemini-api-key
```

### 5. 데이터베이스 마이그레이션
```powershell
flask db upgrade
```

### 6. 앱 실행
```powershell
flask run
```

또는 VS Code에서 `Ctrl+Shift+B` (Flask 서버 실행 태스크)

### 7. 브라우저에서 접속
```
http://localhost:5000
```

## 📊 데이터베이스 모델

### 주요 모델
- **User** - 사용자 계정
- **InstrumentPost** - 중고 거래 게시물
- **BrandInfo** - 악기 브랜드 정보
- **GenreTag** - 장르 태그
- **Comment** - 댓글 (계층 구조 지원)
- **Like** - 좋아요
- **Message** - 1:1 메시지
- **Notification** - 알림
- **Follow** - 팔로우 관계
- **PracticeRecommendation** - AI 추천 기록
- **PracticeSong** - 추천 곡 (진행도 포함)
- **PracticeTechnique** - 추천 기술
- **PracticeLog** - 연습 일지

## 🔑 주요 엔드포인트

### 인증
- `GET/POST /login` - 로그인
- `GET/POST /register` - 회원가입
- `GET /logout` - 로그아웃

### 중고 거래
- `GET /` - 메인 페이지 (게시물 목록)
- `GET/POST /add` - 게시물 작성
- `GET /post/<id>` - 게시물 상세
- `GET/POST /edit/<id>` - 게시물 수정
- `POST /delete/<id>` - 게시물 삭제

### SNS
- `GET /sns` - SNS 피드
- `GET/POST /sns/create` - SNS 게시물 작성
- `GET /sns/<id>` - SNS 게시물 상세
- `POST /sns/like/<id>` - 좋아요 토글
- `POST /sns/<id>/comment` - 댓글 작성

### 메시지
- `GET /messages` - 메시지 목록
- `GET/POST /messages/<user_id>` - 특정 사용자와 대화

### 연습 시스템
- `GET/POST /guitar-practice` - AI 추천 생성
- `POST /practice/save` - 추천 저장
- `GET /practice/my-list` - 내 연습 목록
- `GET /practice/detail/<id>` - 추천 상세
- `POST /practice/update-status` - 진행도 업데이트
- `GET/POST /practice/log` - 연습 일지

## 🌟 개발 예정 기능

- [ ] 실시간 채팅 (WebSocket)
- [ ] 이메일 인증
- [ ] 프로필 사진 업로드
- [ ] 고급 검색 필터 (가격 범위 등)
- [ ] 게시물 북마크
- [ ] 알림 설정 관리
- [ ] 모바일 앱 (React Native)

## 📝 라이선스

MIT License

## 👨‍💻 개발자

- 개발: [Your Name]
- 문의: [Your Email]

---

**Made with ❤️ for musicians**
