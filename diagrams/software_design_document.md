# PythonProject4 — 소프트웨어 설계서

생성일: 2025-12-01
저자: 자동 생성 (지원: GitHub Copilot)

목차에 따라 작성합니다.

1. 개요
1.1 문서의 목적 및 범위

이 문서는 PythonProject4 애플리케이션의 소프트웨어 아키텍처, 클래스 설계, 데이터 설계, 인터페이스, 물리 구조 및 구현 기술을 기술합니다. 목적은 개발팀과 운영팀이 공통 이해를 갖도록 하고, 리팩터링·테스트·배포를 위한 설계 기준을 제공하는 것입니다. 범위는 백엔드(Flask 애플리케이션), 데이터 계층(RDS/Aurora), 캐시 및 비동기 처리(Celery/Redis), 정적 파일 저장(S3/CloudFront) 및 CI/CD( GitHub Actions → ECR → ECS/EKS )를 포함합니다.

1.2 프로젝트 개요

PythonProject4는 악기(또는 기타 상품) 게시물 공유/판매 플랫폼입니다. 핵심 기능은 회원관리(가입/로그인), 게시물 CRUD(다중 이미지), 댓글/좋아요, 피드(순위 기반), 이미지 업로드/처리 및 검색/브랜드/태그 연동입니다. 현재 코드베이스의 핵심 파일: `app/models.py`, `app/routes.py`, `app/routes_auth.py`, `app/dm_interfaces.py`, `app/schemas.py`, `app/hci_interfaces.py`.

1.3 관련 문서, 용어 및 약어

- 관련 문서
  - `diagrams/dm_hci_class_details.md` — 클래스 상세 사양
  - `diagrams/dm_database_schema.sql` / `diagrams/dm_database_schema.md` — DB DDL 및 설명
  - `diagrams/physical_architecture.md` / `diagrams/deployment_diagram.puml` — 물리/배포 아키텍처
  - `diagrams/deployment_specs.md` — 하드웨어·소프트웨어·네트워크 스펙

- 주요 용어/약어
  - DM: Data Model / Domain Model
  - HCI: Human-Computer Interface (여기서는 Presentation/API layer)
  - DB: Database
  - RDS: AWS Relational Database Service
  - S3: AWS Simple Storage Service
  - CDN: Content Delivery Network (CloudFront)
  - API: Application Programming Interface

2. 소프트웨어 아키텍처
2.1 정적구조

2.1.1 패키지 및 모듈

- `app/`
  - `models.py` : SQLAlchemy ORM 엔티티
  - `routes.py`, `routes_auth.py` : HTTP 라우트(Flask)
  - `dm_interfaces.py` : Repository 인터페이스 (PostRepositoryInterface 등)
  - `schemas.py` : HCI DTO (PostCreateDTO 등)
  - `hci_interfaces.py` : Validator/Controller/Renderer 인터페이스

- `scripts/` : utility (PlantUML render, PDF generator)
- `diagrams/` : 설계 문서 및 .puml

2.1.2 클래스 개요

주요 도메인 클래스(요약): `User`, `InstrumentPost`, `PostImage`, `Comment`, `Like`, `Tag/GenreTag`, `BrandInfo` — 상세 속성/메서드는 `diagrams/dm_hci_class_details.md` 참조.

2.2 동적구조

2.2.1 주요 시퀀스(흐름)

- 회원 가입/로그인: `routes_auth` → validator → repository → DB 트랜잭션 → session/cookie 발급
- 게시물 생성: `POST /posts` → `PostCreateDTO` 생성/validated → Service/Create use-case → DB 트랜잭션(포스트/이미지 메타 저장) → S3 업로드(원본) → enqueue worker(thumbnail, search index) → feed invalidate
- 뷰/조회(피드): `GET /feed` → Repository.get_feed(user_id, cursor) → Redis 캐시 확인 → (miss) compute candidates → prefetch images/user → score bằng feed 알고리즘 → cache + return
- 좋아요: API 호출 → Repository.create_like (트랜잭션) → likes_count atomic update → feed cache invalidation / notification

동적 구조(상세 순서도와 시퀀스 다이어그램)는 `diagrams/sequence_*.puml` 파일들을 참조하세요.

3. 클래스 설계
3.1 속성 및 메서드 구체화

참조: `diagrams/dm_hci_class_details.md` 파일에서 다음 클래스들에 대한 상세 정의를 추가했습니다: `User`, `BrandInfo`, `InstrumentPost`, `PostImage`, `Comment`, `Like`, `Tag`, 그리고 Repository 인터페이스 및 HCI DTO. 아래는 핵심 요약입니다.

- User
  - 속성: `id`, `username`(unique), `email`(unique), `password_hash`, `display_name`, `bio`, `is_active`, `created_at`, `updated_at`
  - 메서드: `set_password`, `check_password`, `to_public`

- InstrumentPost
  - 속성: `id`, `user_id`, `title`, `description`, `price`, `brand_id`, `views`, `likes_count`, `comments_count`, `is_published`, `published_at`, `created_at`, `updated_at`
  - 메서드: `increment_views(ip)`, `add_like(user_id, repo)`, `remove_like(...)`, `publish()`, `compute_feed_score(now)`

- PostImage
  - 속성: `id`, `post_id`, `storage_key`, `width`, `height`, `order`, `created_at`
  - 메서드: `generate_thumbnails()`, `get_public_url(size)`

3.2 제약 사항

- 데이터 제약: `username`, `email` unique; `post_images.order` unique per post; `likes` 테이블 unique(post_id,user_id)
- 성능 제약: `likes_count`/`comments_count`는 denormalized counter로, atomic update 또는 Redis 기반 카운터 + 주기적 동기화 필요
- 보안 제약: 비밀번호는 해시(예: bcrypt/argon2), 업로드 파일은 MIME/확장자 검사 및 바이러스 검사 (운영 시)
- 일관성 제약: 작성/삭제와 같은 다중 테이블 변경은 DB 트랜잭션으로 묶고, 외부 작업(썸네일 생성, 검색 인덱스 업데이트)은 트랜잭션 커밋 후 비동기 처리

4. 데이터 설계
4.1 데이터 타입 분석

- 일반 매핑 (권장 SQL 타입)
  - `id`: BIGINT / INT (PK, autoincrement)
  - `username`: VARCHAR(64)
  - `email`: VARCHAR(255)
  - `password_hash`: VARCHAR(255)
  - `title`: VARCHAR(255)
  - `description`: TEXT (마크다운/HTML 저장 시 sanitize)
  - `price`: DECIMAL(12,2)
  - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE (or DATETIME)

4.2 데이터 구조 설계

- 테이블 설계(요약)
  - `users`(id, username, email, password_hash, display_name, bio, is_active, created_at, updated_at)
  - `instrument_posts`(id, user_id, title, description, price, brand_id, views, likes_count, comments_count, is_published, published_at, created_at, updated_at)
  - `post_images`(id, post_id, storage_key, width, height, order, created_at)
  - `comments`(id, post_id, user_id, parent_id, content, created_at, is_deleted)
  - `likes`(id, post_id, user_id, created_at) UNIQUE(post_id,user_id)
  - `tags`, `post_tags`, `brands` 등

자세한 DDL은 `diagrams/dm_database_schema.sql`을 참조하세요. 인덱스: `user_id`, `post_id`, `tag_id`, `username`, `email`에 대해 인덱스를 생성합니다. 텍스트 검색은 Fulltext 또는 외부 검색엔진(Elasticsearch)을 권장합니다.

5. 인터페이스 설계
5.1 외부 시스템 인터페이스

- 스토리지: S3 (REST API, presigned URLs), CloudFront for CDN
- DB: Amazon RDS / Aurora (MySQL compatible) — SQL over TLS
- 캐시/브로커: Redis (ElastiCache) — RESP protocol, TLS optional
- CI/CD: GitHub Actions → ECR push → ECS/EKS deploy (AWS APIs)
- 모니터링: Sentry (HTTP API), Prometheus exporters (metrics endpoint)

5.2 사용자 인터페이스

- Web UI: HTML templates under `app/templates/` rendered server-side (Flask). 주요 엔드포인트:
  - `GET /` : 피드
  - `GET /post/<id>` : 게시물 보기
  - `POST /posts` : 게시물 생성 (multipart/form-data for images)
  - `POST /posts/<id>/like` : 좋아요 API
  - `POST /auth/login`, `POST /auth/register`

- API: REST JSON responses for SPA or mobile client, DTOs defined in `app/schemas.py` (e.g., `PostSummaryDTO`, `PostCreateDTO`).

6. 시스템 물리 구조 설계
6.1 물리 구조 선정

권장: AWS 기반 컨테이너 아키텍처 (CloudFront → ALB → ECS/Fargate or EKS) + RDS(Aurora) + ElastiCache(Redis) + S3. 이유: 관리형 서비스로 가용성·확장성·보안성을 빠르게 확보함.

6.2 패키지 할당

- ALB: 인터넷 트래픽 종료 및 WAF 적용
- App tasks (ECS/EKS): `app` (Flask) 서비스, Nginx + Gunicorn/uvicorn
- Workers: Celery workers on Fargate / EC2 for thumbnail/search indexing
- DB: RDS (Multi-AZ) — persistence
- Cache: Redis — sessions, rate-limiting, temporary counters

배치 다이어그램은 `diagrams/deployment_diagram.puml` 및 `diagrams/deployment_diagram.svg`를 참조하세요.

7. 구현 기술 정의
7.1 소프트웨어 구현 기술

- 언어/런타임: Python 3.11
- 프레임워크: Flask, SQLAlchemy, Alembic (migrations)
- 작업큐: Celery (or SQS as alternative)
- 캐시/브로커: Redis (ElastiCache)
- 컨테이너: Docker, registry: ECR
- 오케스트레이션: ECS (Fargate) or EKS (Kubernetes)
- CI/CD: GitHub Actions
- 모니터링: Prometheus, Grafana, Sentry, CloudWatch

7.2 하드웨어 스펙

자세한 하드웨어·서비스 스펙은 `diagrams/deployment_specs.md`에 저장되어 있습니다. 요약:
- 소규모: `db.t3.medium`, app tasks 0.5 vCPU / 1GB mem
- 중간: `db.r5.large` 또는 Aurora (writer + reader), app tasks 1 vCPU / 2–4GB mem, Redis cluster 2 nodes
- 대규모: Aurora writer+readers (r5.xlarge+), EKS cluster with node groups, Redis sharded cluster

8. 요구사항 추적표

아래 표는 핵심 요구사항(기능)과 설계·구현 위치를 매핑합니다.

| 요구사항 (기능) | 관련 모듈 / 파일 | 참조 문서 |
|---|---:|---|
| 회원가입/로그인 | `app/routes_auth.py`, `app/models.py` | `diagrams/dm_hci_class_details.md` |
| 게시물 생성(다중 이미지) | `app/routes.py`, `app/models.py`, `app/schemas.py` | `diagrams/dm_hci_class_details.md`, `diagrams/dm_database_schema.sql` |
| 이미지 업로드/썸네일 | S3 + Celery workers, `post_images` 테이블 | `diagrams/deployment_specs.md`, `diagrams/dm_hci_class_details.md` |
| 좋아요/댓글 | `app/models.py` (Like, Comment), `app/dm_interfaces.py` | `diagrams/dm_hci_class_details.md` |
| 피드(랭킹) | `PostRepositoryInterface.get_feed`, Redis cache | `diagrams/dm_hci_class_details.md` |
| 검색 / 브랜드 매핑 | `BrandInfo` 엔티티, fulltext 또는 ES | `diagrams/dm_database_schema.md` |

끝.

---

변경 제안 또는 추가 생성 가능한 인공물:
- (A) `app/services/post_service.py` 샘플 구현
- (B) SQLAlchemy 모델 패치 / Alembic 마이그레이션 스크립트
- (C) Terraform 템플릿(VPC, ALB, ECS, RDS) 스켈레톤

원하시는 후속 작업을 선택해 주세요. 
