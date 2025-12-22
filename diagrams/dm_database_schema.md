# DM 데이터베이스 스키마 설계 문서

생성일: 2025-12-01

이 문서는 3계층 아키텍처의 DM 계층(데이터 관리)을 위한 데이터베이스 스키마 설계(정규화, 제약, 인덱스 등)를 설명합니다.

생성한 파일:
- `diagrams/dm_database_schema.sql` — MySQL 호환 DDL

요약 설계 목표:
- 기존 모델(`app/models.py`)을 기반으로 정규화된 테이블 구조 제공
- 검색·필터 성능을 위한 적절한 인덱스 추가
- 태그(장르) 정보를 정규화하여 재사용성 및 검색 효율 개선
- 외래키 제약과 적절한 ON DELETE 정책으로 데이터 무결성 보장

주요 테이블 및 설명:

- `users`: 사용자 계정 저장. `username`에 UNIQUE 및 인덱스 적용.
- `brands`: 브랜드/제조사 정보. 기존 `BrandInfo`를 정규 테이블로 분리.
- `instrument_posts`: 게시글 테이블(게시글 본문, 가격, 상태, 작성자, 브랜드 등). `brand_id`는 NULL 허용(브랜드 미등록 시).
  - `user_id`는 `users.id`에 FK로 CASCADE 삭제
  - `created_at`, `updated_at` 필드로 최신순/변경 추적 가능
- `post_images`: 게시글별 이미지 메타(파일명, 순서)
- `comments`: 댓글(계층형 지원을 위해 `parent_id` 포함)
- `likes`: 좋아요 테이블(유저+포스트에 UNIQUE 제약)
- `my_instruments`: 사용자가 등록한 악기(이미지 JSON 컬럼 포함)
- `tags`, `post_tags`: 태그 테이블 및 게시글-태그 매핑(정규화)
- `model_genres`: 브랜드+모델별 장르 매핑(원래 `GenreTag`의 정규화된 대체)
- `followers`: 팔로우 정보를 저장(소셜 기능 확장)

인덱스 및 성능 고려사항:
- `instrument_posts`에 `brand_id`, `user_id`, `created_at`, `status` 인덱스 추가(필터/정렬 최적화)
- `likes`에 `post_id` 인덱스로 포스트 기준 집계 빠르게 수행
- `instrument_posts.model_name`에 접두사 인덱스(예: 64)로 검색 성능 향상

제약 및 삭제 정책 권장:
- `user` 삭제 시 관련 `instrument_posts`, `comments`, `likes`, `my_instruments`를 CASCADE로 삭제하여 고아 레코드 방지
- `brand` 삭제 시 기존 게시글의 `brand_id`를 NULL 처리(기록 보존)

마이그레이션/적용 계획(권장):
1. 새로운 테이블(`tags`, `post_images`, `model_genres`, `followers`)을 추가
2. 기존 `GenreTag` 데이터 변환 스크립트 작성(문자열 → 태그 레코드 + model_genres 연결)
3. 점진적으로 `instrument_posts.images` JSON에서 `post_images`로 마이그레이션(혹은 둘 다 유지)
4. 리포지토리 계층에서 새로운 테이블을 사용하는 구현 작성 및 테스트

테스트 아이디어:
- 스키마 제약 테스트: foreign key 제약, unique 제약, cascade 동작 확인
- 성능 테스트: 대량 데이터에서의 인덱스 효과(브랜드/모델/태그 필터)

파일 사용 방법:
- 로컬 MySQL로 적용 테스트: `mysql -u user -p database < diagrams/dm_database_schema.sql`  
- SQLAlchemy 모델 동기화: 파일을 참조하여 `app/models.py`에 반영하거나 Alembic 마이그레이션으로 적용

문의/확장 제안:
- 검색(Full-Text) 기능이 필요하면 `instrument_posts(title, description)`에 FT 인덱스 추가 검토
- 이미지 저장을 파일 시스템에서 S3 등 외부 스토리지로 이관하는 경우 `post_images` 레코드는 메타만 관리