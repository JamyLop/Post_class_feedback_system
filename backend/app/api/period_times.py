"""节次时间配置 API：管理员和德育主任维护全校节次时间。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.period_time import PeriodTime
from app.models.user import ROLE_ADMIN, ROLE_DEYU_DIRECTOR, User
from app.schemas.period_time import PeriodTimeOut, PeriodTimeUpdate

router = APIRouter(prefix="/period-times", tags=["period-times"])
_time_manager = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR])


@router.get("", response_model=list[PeriodTimeOut])
def list_period_times(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(PeriodTime).order_by(PeriodTime.period).all()


@router.put("/{period}", response_model=PeriodTimeOut)
def update_period_time(
    period: int,
    body: PeriodTimeUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_time_manager),
):
    if period < 1 or period > 12:
        raise HTTPException(status_code=422, detail="节次必须在 1-12 之间")
    pt = db.query(PeriodTime).filter(PeriodTime.period == period).first()
    if pt is None:
        raise HTTPException(status_code=404, detail="该节次不存在")
    pt.start_time = body.start_time
    pt.end_time = body.end_time
    db.commit()
    db.refresh(pt)
    return pt
