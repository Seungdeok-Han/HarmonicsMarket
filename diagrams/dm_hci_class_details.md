# DM / HCI 클래스 상세 설계

생성일: 2025-12-01

이 문서는 `app/models.py` 기반 도메인 클래스(영속화 계층, DM)와 HCI/DTO 계층(`app/schemas.py`, `app/hci_interfaces.py`)에 대해 각 클래스의 필드(타입·제약), 주요 메서드 시그니처, 핵심 알고리즘/비즈니스 로직(의사코드)을 기술합니다. 이 문서는 리팩터링/구현·테스트·마이그레이션 작업의 사양서로 사용하세요.

각 섹션은 다음을 포함합니다:
- 속성: 필드 이름, 타입, 제약(필수/nullable/unique/인덱스), 기본값
- 관계: 외래키/연관관계 요약
- 메서드: 시그니처(파라미터, 반환값), 동작 설명 및 의사코드(알고리즘/트랜잭션/에러 처리)

--

## 1) User

- 속성
  - `id: int` — PK, autoincrement
  - `username: str` — unique, indexed, length <= 64
  - `email: str` — unique, indexed, email format
  - `password_hash: str` — salted hash (bcrypt/argon2)
  - `display_name: Optional[str]` — nullable, length <= 128
  - `bio: Optional[str]` — nullable, length <= 1000
  - `is_active: bool` — default True
  - `created_at: datetime`, `updated_at: datetime` — timestamps

- 관계
  - one-to-many: `InstrumentPost` (author)
  - one-to-many: `Comment`
  - many-to-many: followers/following (UserFollow 테이블 권장)

- 메서드
  - `check_password(self, password: str) -> bool` — bcrypt.checkpw or argon2 verify
  - `set_password(self, password: str) -> None` — store hashed password
  - `to_public(self) -> dict` — 필수 공개 필드만 반환 (no password)

예시(의사코드):
```python
def set_password(self, password: str) -> None:
    self.password_hash = hash_password(password)  # use bcrypt/argon2

def check_password(self, password: str) -> bool:
    return verify_password(password, self.password_hash)

def to_public(self) -> dict:
    return {"id": self.id, "username": self.username, "display_name": self.display_name}
```

--

## 2) BrandInfo

- 속성
  - `id: int` PK
  - `name: str` unique, indexed
  - `description: Optional[str]`
  - `origin_country: Optional[str]`
  - `created_at`, `updated_at`

- 메서드
  - `search_by_name(query: str) -> Query` — normalized search (lowercase, strip)

알고리즘 노트: 브랜드명 검색은 `ILIKE` + trigram 인덱스 또는 ElasticSearch 사용 권장.

--

## 3) InstrumentPost

- 속성
  - `id: int` PK
  - `user_id: int` FK -> users.id, indexed
  - `title: str` length <= 255
  - `description: Optional[str]` (markdown/html sanitized)
  - `price: Optional[Decimal]` (currency 적용)
  - `brand_id: Optional[int]` FK
  - `views: int` default 0
  - `likes_count: int` denormalized counter default 0 (atomic updates)
  - `comments_count: int` denormalized counter default 0
  - `is_published: bool`, `published_at: Optional[datetime]`
  - `created_at`, `updated_at`

- 관계
  - one-to-many: `PostImage`
  - one-to-many: `Comment`
  - many-to-many: `Tag` via `PostTags`

- 메서드 (핵심)
  - `increment_views(self, ip: Optional[str]=None) -> None`
    - 목적: 조회수 증가(중복 방지 로직은 캐시 기반)
    - 구현: Redis에 키 `post:{id}:views:recent` 로 IP/유저 토큰을 짧게 저장(예: 1분). 존재하지 않으면 RDS에 `views += 1` 하고 Redis에 플래그 추가.

  - `add_like(self, user_id: int, repo: PostRepository) -> bool`
    - 목적: 좋아요 등록/중복 방지
    - 구현: 트랜잭션으로 `likes` 테이블에 (user_id, post_id) insert 시도. 중복키 에러 -> False. 성공 -> increment `likes_count` (atomic SQL + 캐시 invalidate)

  - `remove_like(self, user_id: int, repo: PostRepository) -> bool`
    - 트랜잭션으로 삭제 후 `likes_count` 감소.

  - `publish(self) -> None`
    - set `is_published=True`, `published_at=now()`, enqueue indexing task (search index) 및 feed-cache invalidation.

  - `compute_feed_score(self, now: datetime) -> float`
    - feed ranking 점수(예시): score = w1 * log(1 + likes_count) + w2 * log(1 + comments_count) + w3 * recency_decay
    - recency_decay = max(0, 1 - (now - published_at).total_seconds() / HALF_LIFE)

의사코드(간단):
```python
def increment_views(self, ip=None):
    key = f"post:{self.id}:views:{ip or 'anon'}"
    if not redis.exists(key):
        with db.session.begin():
            db.session.execute("UPDATE instrument_post SET views = views + 1 WHERE id = :id", {"id": self.id})
        redis.set(key, 1, ex=60)

def add_like(self, user_id, repo):
    try:
        with db.session.begin():
            repo.create_like(self.id, user_id)
            db.session.execute("UPDATE instrument_post SET likes_count = likes_count + 1 WHERE id = :id", {"id": self.id})
        return True
    except IntegrityError:
        return False
```

성능/일관성 노트: likes_count는 denormalized counter이므로 DB 트랜잭션에서 안전하게 업데이트하거나 Redis-based counter를 사용하고 정기적으로 스냅샷(sync) 하십시오.

--

## 4) PostImage

- 속성
  - `id: int` PK
  - `post_id: int` FK
  - `storage_key: str` (S3 path)
  - `width: Optional[int]`, `height: Optional[int]`
  - `order: int` 게시물 내 정렬순
  - `created_at`

- 메서드
  - `generate_thumbnails(self) -> list[str]`
    - 워커에서 S3에 썸네일 생성(최대 3종류). 썸네일 키를 DB에 업데이트.
  - `get_public_url(self, size='orig') -> str` — presigned URL 또는 CloudFront URL 반환

워크플로우: 업로드 → S3 저장(원본) → DB에 메타 저장 → Celery 워커가 썸네일 생성 → DB 업데이트 → CDN invalidation

--

## 5) Comment

- 속성
  - `id`, `post_id`, `user_id`, `parent_id`(threaded replies), `content`, `created_at`, `is_deleted`

- 메서드
  - `add_reply(self, user_id, content) -> Comment` — parent/child 관계 생성, 트랜잭션으로 댓글 카운터 증가
  - `soft_delete(self, actor_user_id) -> bool` — 작성자 또는 관리자만 삭제 가능. `is_deleted=True` 처리

--

## 6) Like

- 속성
  - `id`, `post_id`, `user_id`, `created_at` — unique(post_id, user_id)

- 메서드: 주로 repository 수준에서 처리(생성/삭제 트랜잭션 관리)

--

## 7) Tag / GenreTag

- 속성
  - `id`, `name` (normalized), `type`(genre|custom)

- 메서드
  - `normalize_name(name: str) -> str` — lowercase, strip, unicode normalize
  - `bulk_attach_to_post(post_id, tag_names)` — 사용량 많은 경우 배치+upsert

--

## 8) Repository 인터페이스(요약)

아래는 `app/dm_interfaces.py`에서 정의한 repository contract에 대한 상세 동작 명세(시그니처·트랜잭션·캐시 고려).

- `PostRepositoryInterface` (핵심 메서드)
  - `get_by_id(post_id: int) -> InstrumentPost | None`
  - `create_post(dto: PostCreateDTO) -> InstrumentPost`
  - `update_post(post_id: int, dto: PostUpdateDTO) -> InstrumentPost`
  - `delete_post(post_id: int) -> None`
  - `list_posts_by_user(user_id: int, cursor: Optional[str], limit: int) -> List[InstrumentPost]` — cursor 기반 페이지네이션
  - `get_feed(user_id: int, cursor: Optional[str], limit: int) -> List[InstrumentPost]` — feed 알고리즘 적용 (DB + cache hybrid)
  - `create_like(post_id: int, user_id: int) -> Like` — insert, raise IntegrityError on duplicate
  - `remove_like(post_id: int, user_id: int) -> bool`

Repository 알고리즘 요약 (get_feed):
1. Check Redis cache for `feed:user:{user_id}:{cursor}`; if hit return cached list.
2. If miss, query candidate posts: recent published posts where (author in followings OR popular posts), order by score computed via SQL expression or by fetching engagement counters and applying score in application layer.
3. Prefetch images and user display_name via JOINs to avoid N+1.
4. Cache rendered feed keys for short TTL (30-120s) and apply cache invalidation on new publish/like threshold events.

--

## 9) HCI / DTO (app/schemas.py)

- `PostCreateDTO`
  - `user_id: int` (server side), `title: str`, `description: str`, `price: Optional[Decimal]`, `brand_id: Optional[int]`, `tags: List[str]`, `images: List[UploadFile]`
  - Validation:
    - `title` length 3..255
    - `description` max 5000
    - `price` >= 0 (if provided)
    - `images` max 10 files, each size <= 10MB, allowed MIME types

- `PostSummaryDTO` — feed에서 반환
  - `id, title, short_description, main_image_url, likes_count, comments_count, created_at, author: {id, username, display_name}`

- `UserRegisterDTO` — validation: email format, password complexity

Validation algorithm: use HCI-level `IValidator` that runs field validators, returns aggregated error map. Example: password complexity uses regex + entropy heuristic (min length + char classes).

--

## 10) Controller / Service responsibilities (IController / IPostController)

- Controller (HCI layer) tasks
  - Parse HTTP request -> DTO
  - Run validators -> return 400 with error details
  - Call Service / Use-case interactor
  - Translate domain objects -> DTOs/ApiResponse

- Service (Domain use-case) tasks
  - Enforce business rules and transactions (e.g., create post: store post row, store images meta, enqueue thumbnail tasks, index post)
  - Should be thin and testable: `PostService.create_post(dto, current_user)`

트랜잭션 예시(생성 흐름):
1. Begin DB transaction
2. Insert `instrument_post` row
3. Insert `post_images` rows
4. Commit
5. Enqueue async tasks (thumbnail, search index, feed invalidation)

--

## 11) Feed ranking 알고리즘 (간략 사양)

- 목표: 신선도 + 참여도 기반 우선순위
- 점수 함수(예시):

  score(post) = A * log(1 + likes) + B * log(1 + comments) + C * recency_factor + D * author_reliability

  - recency_factor = exp(-(now - published_at) / tau)  # tau: 시간 상수 (예: 48h)
  - author_reliability = function(follower_count, recent_engagement_rate)

- 구현 권장
  - 1차: SQL에서 likes_count, comments_count, published_at를 조회해 애플리케이션 레이어에서 score 계산
  - 2차(확장): Precompute score periodically in materialized view or in Redis zset per user (sorted by score)

의사코드(간단):
```python
def compute_score(likes, comments, published_at, now=datetime.utcnow()):
    recency = math.exp(-(now - published_at).total_seconds() / (3600*24*2))
    return 1.2 * math.log1p(likes) + 0.8 * math.log1p(comments) + 2.0 * recency
```

--

## 12) 일관성·성능 권장사항 요약

- 인덱스: FK 컬럼(user_id, post_id, tag_id)에 인덱스 추가. 텍스트 검색 필드(title, description)는 fulltext 또는 외부 검색엔진 추천.
- 카운터: likes_count/comments_count는 DB에서 atomic update 하거나 Redis counter + periodic reconciliation.
- 캐시: feed와 thumbnail URL은 CDN + Redis로 캐시, invalidation을 짧게 유지.
- 트랜잭션: 여러 테이블을 건드리는 작업은 DB 트랜잭션에서 묶되, 외부 작업(enqueue, s3 upload)은 트랜잭션 외부에서 비동기로 처리.

--

## 13) 테스트 아이디어

- 단위 테스트
  - `InstrumentPost.add_like`의 동시성 테스트 (동시에 100 요청)
  - `increment_views`가 동일 IP에 대해 TTL 작동
  - DTO validator 경계값 테스트(title length, image count)

- 통합 테스트
  - 게시물 생성(파일 업로드 -> worker가 썸네일 생성 -> DB 업데이트)
  - feed pagination cursor 일관성 테스트

--

파일 참조
- `app/models.py` — ORM 매핑
- `app/dm_interfaces.py` — repository contracts
- `app/schemas.py`, `app/hci_interfaces.py` — DTO와 컨트롤러 인터페이스

원하시면 이 명세를 바탕으로:
- (A) SQLAlchemy 모델 스켈레톤 변경 패치 생성
- (B) `app/services/post_service.py` 같은 서비스 레이어 예제 구현
- (C) 단위 테스트 템플릿(pytest) 생성

원하시는 다음 작업을 알려주세요. 예: `A` 로 진행하면 변경 패치를 만들고 테스트를 추가해 드립니다.
