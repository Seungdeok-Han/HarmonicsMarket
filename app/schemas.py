from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PostCreateDTO:
    title: str
    brand_id: Optional[int]
    model_name: Optional[str]
    shape: Optional[str]
    condition: Optional[str]
    price: Optional[float]
    description: Optional[str]
    images: Optional[List[str]]  # 업로드된 파일명 목록


@dataclass
class PostUpdateDTO:
    id: int
    title: Optional[str] = None
    brand_id: Optional[int] = None
    model_name: Optional[str] = None
    shape: Optional[str] = None
    condition: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None


@dataclass
class CommentCreateDTO:
    post_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None


@dataclass
class UserRegisterDTO:
    username: str
    password: str


@dataclass
class UserPublicDTO:
    id: int
    username: str


@dataclass
class LikeResponseDTO:
    liked: bool
    like_count: int
