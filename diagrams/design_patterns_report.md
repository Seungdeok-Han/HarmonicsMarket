# DM & HCI 계층 보고서

작성자: 자동생성
생성일: 2025-12-01

## 1. 개요

이 문서는 본 프로젝트(PythonProject4)를 3계층 아키텍처(Presentation/HCI, Business Logic, Data/DM) 관점에서 분석하여
DM(Data Management) 계층과 HCI(Human-Computer Interaction) 계층에서 정의되어야 할 클래스(엔티티, DTO, 인터페이스)를 정리합니다.

대상: 개발자, 코드 리뷰어, 테스터

## 2. 아키텍처 요약

- Presentation (HCI): 사용자 인터페이스, 템플릿, 요청/응답 처리 (`templates/`, `static/`, `app/routes.py`)  
- Business Logic (BL): 애플리케이션의 서비스 로직(현재는 `routes.py`가 일부 담당), 권장: `app/services/`에 이식  
- Data Management (DM): 데이터 모델(ORM), 영속성, Repository (`app/models.py`, `app/migrations/`)

## 3. DM 계층 (Data Management)

### 목적/책임

- 데이터 스키마와 영속성 규칙 관리
- 트랜잭션/쿼리 집약 로직의 캡슐화(Repository)
- 모델 제약(Unique, FK, cascade) 관리

### 주요 엔티티(요약)

- `InstrumentPost` (`app/models.py`)  
  - 책임: 게시글 데이터 저장(제목, 브랜드, 모델명, 상태, 가격, 이미지, 작성자 등)  
  - 주요 필드: `id, title, brand_id(FK), model_name, price, user_id(FK), images(JSON), views, status, created_at`

- `User` (`app/models.py`)  
  - 책임: 사용자 계정/인증 관련 데이터  
  - 주요 필드: `id, username, password_hash`

- `Comment`, `Like`, `BrandInfo`, `MyInstrument`, `GenreTag` 등

### Repository 인터페이스 (권장)

Repository는 DM 계층의 추상화 레이어로, 서비스(BL)가 DB 구현 세부사항에 의존하지 않도록 합니다. 예시 인터페이스:

```python
class PostRepositoryInterface(ABC):
    def get_by_id(self, post_id: int) -> Optional[InstrumentPost]:
        pass
    def list(self, filters: dict = None, page: int = 1, per_page: int = 20) -> List[InstrumentPost]:
        pass
    def add(self, post: InstrumentPost) -> InstrumentPost:
        pass
    def update(self, post: InstrumentPost) -> InstrumentPost:
        pass
    def delete(self, post_id: int) -> None:
        pass
```

파일: `app/dm_interfaces.py` (인터페이스 정의)

### 테스트 아이디어 (DM)

- Repository CRUD 테스트: SQLite in-memory 이용  
- 모델 제약(Unique, FK) 단위 테스트  
- 마이그레이션 적용/롤백 검증

## 4. HCI 계층 (Presentation)

### 목적/책임

- 사용자 입력(폼/JSON) 수신 및 기본 유효성 검사  
- 입력을 DTO로 변환하여 BL로 전달  
- 템플릿 렌더링과 JSON 응답 생성

### DTO / Schema (권장)

요청과 응답의 표준화를 위해 DTO를 사용하면 라우트 테스트와 서비스 호출이 명확해집니다. 예시 DTO:

```python
@dataclass
class PostCreateDTO:
    title: str
    brand_id: Optional[int]
    model_name: Optional[str]
    shape: Optional[str]
    condition: Optional[str]
    price: Optional[float]
    description: Optional[str]
    images: Optional[List[str]]

@dataclass
class CommentCreateDTO:
    post_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None
```

파일: `app/schemas.py`

### HCI 테스트 아이디어

- DTO 유효성 검사 단위 테스트  
- Flask test client를 이용한 라우트 통합 테스트(폼 제출, JSON 응답 검사)

## 5. 시퀀스 예시 (요약)

1. 게시글 생성(Create Post) 흐름:  
   HCI(routes.add_post) → DTO(PostCreateDTO) → BL(PostService) → DM(PostRepository) → DB  
2. 댓글 추가(Add Comment):  
   HCI(routes.add_comment) → DTO(CommentCreateDTO) → BL(CommentService) → DM(CommentRepository) → DB

(자세한 시퀀스 다이어그램은 `diagrams/` 내 시퀀스 파일 참조)

## 6. 적용 전략(점진적 마이그레이션)

1. 우선 신규 기능에서 DTO와 Repository 인터페이스 적용  
2. 서비스 레이어(`app/services/`)를 도입하여 기존 `routes.py`의 비즈니스 로직을 위임  
3. 기존 코드 리팩터링: 단계별로 테스트 추가 후 리팩터링 수행

## 7. 검증 체크리스트

- [ ] 모든 모델이 `app/models.py`에 문서화되어 있는가?  
- [ ] Repository 인터페이스가 `app/dm_interfaces.py`에 정의되어 있는가?  
- [ ] DTO/Schema가 `app/schemas.py`에 정의되어 있는가?  
- [ ] 주요 흐름(게시글 생성, 댓글, 좋아요)이 다이어그램으로 포함되어 있는가?  

## 부록: 관련 파일

- `app/models.py` — ORM 엔티티  
- `app/dm_interfaces.py` — DM 인터페이스(이미 추가됨)  
- `app/schemas.py` — HCI DTO(이미 추가됨)  
- `diagrams/dm_hci_classes.puml` — DM/HCI 클래스 다이어그램  

# 설계 패턴 적용 보고서

작성일: 2025-11-23

## 요약

이 문서는 본 프로젝트의 UML 다이어그램에 적용된 설계 패턴들을 정리한 보고서입니다. 각 패턴에 대해 개요, 프로젝트 내 매핑(클래스/컴포넌트), 구현 스케치, 장단점, 검증 포인트 및 엣지 케이스를 설명합니다.

## 적용된 패턴 목록

- Repository
- Factory
- Singleton
- Observer
- Strategy
- Adapter
- Facade (Service)
- Command

---

## 1. Repository 패턴

1) 요약
- 데이터 접근(영속성) 로직을 도메인/비즈니스 로직과 분리하는 패턴입니다. DB 쿼리, 페이징, 필터링 등을 캡슐화합니다.

2) 프로젝트 매핑
- PostRepository, UserRepository 등 (다이어그램: PostRepository)

3) 구현 스케치(의사코드)
```
interface PostRepository:
    def add(post) -> Post
    def get(id) -> Post
    def list_by_user(user_id, page, per_page)
    def find_by_filters(filters)
```

4) 장점
- 테스트가 쉬워짐(목 스텁 교체)
- 관심사 분리

5) 단점
- 레이어가 하나 늘어남: 간단한 CRUD만으로도 오버헤드 발생 가능

6) 검증 포인트
- Mock Repository로 서비스 계층 단위 테스트
- 페이징/정렬 경계값 테스트

---

## 2. Factory 패턴

1) 요약
- 복잡한 객체 생성 로직을 캡슐화하고 중앙화합니다. 입력(폼, 파일) → 도메인 객체 변환 책임을 가집니다.

2) 프로젝트 매핑
- PostFactory, ConcretePostFactory

3) 구현 스케치
```
class PostFactory:
    def create_from_form(form_data, files) -> InstrumentPost
```

4) 장점
- 생성 책임 분리로 유지보수 용이

5) 단점
- 너무 많은 팩토리 클래스를 만들면 복잡성 증가

6) 검증 포인트
- 이미지 없음, 유효/무효 유튜브 URL 등의 다양한 입력 테스트

---

## 3. Singleton 패턴

1) 요약
- 애플리케이션 전역에서 하나만 존재해야 할 리소스(DB 엔진, 세션 팩토리 등)를 관리합니다.

2) 프로젝트 매핑
- Database, DBSessionProvider (싱글톤으로 사용)

3) 구현 스케치
```
class Database:
    @classmethod
    def instance() -> Database
    def get_session() -> Session
```

4) 장점
- 리소스 일관성 및 절약

5) 단점
- 전역 상태로 인해 테스트 어려움(의존성 주입 권장)

6) 검증 포인트
- 테스트 시 인메모리 DB로 교체 가능한지

---

## 4. Observer 패턴

1) 요약
- 한 객체의 상태 변경을 여러 구독자에게 알리는 패턴입니다. 이벤트 기반 확장성에 유리합니다.

2) 프로젝트 매핑
- FeedPublisher, FollowerObserver, NotificationService

3) 구현 스케치
```
class FeedPublisher:
    def subscribe(subscriber)
    def unsubscribe(subscriber)
    def publish(post)  # 각 subscriber.notify(post) 호출

class FollowerObserver:
    def notify(post)
```

4) 장점
- 느슨한 결합, 구독자 확장 용이

5) 단점
- 이벤트 실패/순서 제어 복잡도

6) 검증 포인트
- 구독자 등록/해제 시 알림 전달 확인
- 한 구독자 실패시 다른 구독자 영향 차단

---

## 5. Strategy 패턴

1) 요약
- 알고리즘(정렬, 필터 등)을 캡슐화하여 런타임에 교체할 수 있게 합니다.

2) 프로젝트 매핑
- SortStrategy, RecentFirstStrategy, PopularityStrategy, PersonalizedStrategy

3) 구현 스케치
```
class SortStrategy:
    def sort(posts) -> list[Post]

service.set_strategy(RecentFirstStrategy())
```

4) 장점
- 전략별로 단위 테스트 가능, 교체성 우수

5) 단점
- 전략 수 증가 시 관리 비용

6) 검증 포인트
- 각 전략이 기대 결과를 반환하는지
- 동일 타임스탬프/빈 리스트 경계값

---

## 6. Adapter 패턴

1) 요약
- 외부 API(YouTube 등)를 내부 인터페이스로 변환하여 결합도를 낮춥니다.

2) 프로젝트 매핑
- YouTubeAdapter (VideoSearchAdapter 인터페이스)

3) 구현 스케치
```
class YouTubeAdapter:
    def search(query) -> List[Video]
```

4) 장점
- 외부 제공자의 교체, 모킹이 쉬움

5) 단점
- 어댑터 코드 추가

6) 검증 포인트
- 외부 API의 다양한 응답(빈 결과, 오류) 변환 검증

---

## 7. Facade (Service) 패턴

1) 요약
- 복잡한 하위 시스템(팩토리, 리포지토리, 스토리지, 퍼블리셔 등)을 단순한 인터페이스로 감쌉니다.

2) 프로젝트 매핑
- PostService (또는 PostFacade)

3) 구현 스케치
```
class PostService:
    def create_post(user, form_data):
        post = factory.create_from_form(form_data)
        repo.add(post)
        publisher.publish(post)
        return post
```

4) 장점
- 호출부 단순화, 트랜잭션 경계 설정 용이

5) 단점
- Facade가 비대해지면 단일 수정 포인트가 됨

6) 검증 포인트
- 하위 컴포넌트 호출 순서/예외 처리 검증(mocks 사용)

---

## 8. Command 패턴

1) 요약
- 요청(행위)을 객체로 캡슐화하여 큐잉, 재시도, 로깅, undo 등을 가능하게 합니다.

2) 프로젝트 매핑
- ICommand, LikeCommand, CommentCommand, CommandInvoker

3) 구현 스케치
```
class LikeCommand(ICommand):
    def __init__(user_id, post_id)
    def execute(): repo.add_like(user_id, post_id)
    def undo(): repo.remove_like(user_id, post_id)
```

4) 장점
- 비동기 큐잉 및 재시도/로깅 구현에 유리

5) 단점
- 단순 연산에 적용하면 불필요한 복잡성

6) 검증 포인트
- execute/undo 동작 및 idempotency 검증

---

## 시퀀스 다이어그램과 패턴 연계 요약

- 포스트 생성: Controller → PostService(Facade) → PostFactory → PostRepository → FeedPublisher(Observer) → Followers
- 좋아요/댓글: Controller → CommandInvoker → LikeCommand/CommentCommand → Repository → Notification/Publisher
- 피드 조회: FeedService → Repository → Strategy.sort(posts)

## 테스트 및 운영 권고

- 단위 테스트: Repository/Factory/Strategy/Command 각각의 단위 테스트 작성
- 통합 테스트: PostService 전체 흐름 (성공/실패 트랜잭션 경계)
- 운영: 대량 팔로워 이벤트는 비동기 큐(RabbitMQ/Redis Streams)로 오프로드. 외부 API 키는 비밀 저장소에 보관.

## 부록: 파일/클래스 매핑

- `app/models.py`: 도메인 모델 (InstrumentPost, User, Comment, Like 등)
- `diagrams/*.puml`: PlantUML 소스 (class_diagram.puml, usecase_diagram.puml, sequence_*.puml)
- `diagrams/*.svg`: 렌더된 SVG 이미지

---

원하시면 이 MD를 PDF로 변환해 repo에 추가해 드립니다. (지금 변환할까요?)
