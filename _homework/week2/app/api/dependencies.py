from typing import Annotated

from fastapi import Depends, Header


def get_current_user_id(x_user_id: Annotated[int, Header()]) -> int:
    """Упрощённая авторизация ДЗ: идентификатор пользователя из заголовка X-User-Id."""
    return x_user_id


UserIdDep = Annotated[int, Depends(get_current_user_id)]
