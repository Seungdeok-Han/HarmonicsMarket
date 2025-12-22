from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ApiResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class IValidator(ABC):


    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """유효하면 (True, {}), 아니면 (False, {'field':'error msg'}) 반환"""
        pass


class IRenderer(ABC):
    """뷰/응답 렌더링 추상화

    - 서버사이드 템플릿 렌더링, JSON 응답 래핑 등을 캡슐화
    """

    @abstractmethod
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def render_json(self, payload: ApiResponse, status: int = 200) -> Tuple[Dict[str, Any], int]:
        pass


class IAuthController(ABC):

    @abstractmethod
    def login(self, form_data: Dict[str, Any]) -> ApiResponse:
        pass

    @abstractmethod
    def logout(self, user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def register(self, form_data: Dict[str, Any]) -> ApiResponse:
        pass


class IPostController(ABC):

    @abstractmethod
    def list_posts(self, params: Dict[str, Any]) -> ApiResponse:
        pass

    @abstractmethod
    def get_post(self, post_id: int, current_user_id: Optional[int] = None) -> ApiResponse:
        pass

    @abstractmethod
    def create_post(self, dto: Dict[str, Any], current_user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def update_post(self, post_id: int, dto: Dict[str, Any], current_user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def delete_post(self, post_id: int, current_user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def toggle_like(self, post_id: int, user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def add_comment(self, post_id: int, dto: Dict[str, Any], user_id: int) -> ApiResponse:
        pass


class IProfileController(ABC):
    @abstractmethod
    def mypage(self, user_id: int) -> ApiResponse:
        pass

    @abstractmethod
    def add_my_instrument(self, dto: Dict[str, Any], user_id: int) -> ApiResponse:
        pass


# 추가적으로, ViewModel 빌더 인터페이스를 정의할 수 있음
class IViewModelBuilder(ABC):

    @abstractmethod
    def build_post_list(self, service_result: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def build_post_detail(self, service_result: Dict[str, Any], current_user_id: Optional[int]) -> Dict[str, Any]:
        pass
