from abc import ABC, abstractmethod
from typing import List, Optional, Any
from .models import InstrumentPost, User, Comment


class PostRepositoryInterface(ABC):
    """데이터 접근 계층(DM)에서 게시글을 다루는 Repository 인터페이스
    실제 구현은 SQLAlchemy 세션을 사용한 클래스가 담당합니다.
    """

    @abstractmethod
    def get_by_id(self, post_id: int) -> Optional[InstrumentPost]:
        pass

    @abstractmethod
    def list(self, filters: dict = None, page: int = 1, per_page: int = 20) -> List[InstrumentPost]:
        pass

    @abstractmethod
    def add(self, post: InstrumentPost) -> InstrumentPost:
        pass

    @abstractmethod
    def update(self, post: InstrumentPost) -> InstrumentPost:
        pass

    @abstractmethod
    def delete(self, post_id: int) -> None:
        pass


class UserRepositoryInterface(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    def add(self, user: User) -> User:
        pass


class CommentRepositoryInterface(ABC):
    @abstractmethod
    def add(self, comment: Comment) -> Comment:
        pass

    @abstractmethod
    def delete(self, comment_id: int) -> None:
        pass


class LikeRepositoryInterface(ABC):
    @abstractmethod
    def toggle_like(self, user_id: int, post_id: int) -> bool:
        """좋아요 토글: True=좋아요 생성, False=좋아요 삭제"""
        pass


# 간단한 팩토리 인터페이스 예시(필요시 사용)
class RepositoryFactoryInterface(ABC):
    @abstractmethod
    def create_post_repository(self) -> PostRepositoryInterface:
        pass

    @abstractmethod
    def create_user_repository(self) -> UserRepositoryInterface:
        pass
