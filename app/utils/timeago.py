from __future__ import annotations

from datetime import datetime
from typing import Optional, Union


def time_ago(value: Union[str, datetime, None], *, now: Optional[datetime] = None) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    now = now or datetime.now()
    delta = now - value
    if delta.days >= 1:
        return f"{delta.days}일 전"
    if delta.seconds >= 3600:
        return f"{delta.seconds // 3600}시간 전"
    if delta.seconds >= 60:
        return f"{delta.seconds // 60}분 전"
    return '방금'
