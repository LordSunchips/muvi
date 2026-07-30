from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import CurrentUser, SessionDep
from app.models import DisplayMetric, UserSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    display_metric: DisplayMetric


class UpdateSettingsRequest(BaseModel):
    display_metric: DisplayMetric


def _ensure_settings(session, user_id: int) -> UserSettings:
    row = session.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(user_id=user_id)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


@router.get("", response_model=SettingsOut)
def get_settings(user: CurrentUser, session: SessionDep) -> SettingsOut:
    assert user.id is not None
    row = _ensure_settings(session, user.id)
    return SettingsOut(display_metric=row.display_metric)


@router.patch("", response_model=SettingsOut)
def update_settings(payload: UpdateSettingsRequest, user: CurrentUser, session: SessionDep) -> SettingsOut:
    assert user.id is not None
    row = _ensure_settings(session, user.id)
    row.display_metric = payload.display_metric
    session.add(row)
    session.commit()
    session.refresh(row)
    return SettingsOut(display_metric=row.display_metric)
