"""认证路由：登录 / 当前用户 / 邀请码注册 / 微信小程序登录绑定。"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM, create_access_token, hash_password, verify_password
from app.models.class_ import StudentGuardian
from app.models.invite import (
    INVITE_STATUS_ACTIVE,
    INVITE_STATUS_USED,
    InviteCode,
)
from app.models.student_case import StudentCase
from app.models.user import ROLE_CONSULTANT, ROLE_DEYU_DIRECTOR, ROLE_PARENT, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.models.user_external_identity import UserExternalIdentity
from app.schemas.admin import RegisterRequest
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.schemas.wx_auth import ChildBrief, WxBindRequest, WxLoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

# 内存级一次性票据去重（进程内）；生产多实例建议换 Redis/DB 持久化
_consumed_bind_jtis: set[str] = set()


def _create_bind_ticket(openid: str, unionid: str | None) -> str:
    jti = uuid.uuid4().hex
    payload = {
        "purpose": "wx_bind",
        "openid": openid,
        "unionid": unionid,
        "app_id": settings.wx_appid or "default",
        "jti": jti,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=300),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _verify_bind_ticket(ticket: str) -> dict:
    try:
        payload = jwt.decode(ticket, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="bind_ticket 无效或已过期") from exc
    if payload.get("purpose") != "wx_bind":
        raise HTTPException(status_code=400, detail="bind_ticket 用途错误")
    jti = payload.get("jti")
    if not jti or jti in _consumed_bind_jtis:
        raise HTTPException(status_code=400, detail="bind_ticket 已使用或无效")
    return payload


def _consume_jti(jti: str) -> None:
    _consumed_bind_jtis.add(jti)
    # 简单防内存无限增长：超过 10000 条清空一半
    if len(_consumed_bind_jtis) > 10000:
        # set 无序，直接丢弃一半（创建新 set）
        items = list(_consumed_bind_jtis)
        _consumed_bind_jtis.clear()
        _consumed_bind_jtis.update(items[5000:])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """账号密码登录，签发 JWT。"""
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token(user.id, user.role)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return user


@router.post("/wx-login")
async def wx_login(body: WxLoginRequest, db: Session = Depends(get_db)):
    """微信小程序登录：code -> openid；已绑定直发 JWT，未绑定返一次性 bind_ticket。"""
    code = (body.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")
    # 严禁客户端直接提交 openid，必须服务端调微信
    try:
        from app.services.wx_service import jscode2session

        openid, unionid = await jscode2session(code)
    except ValueError as exc:
        # 不回退 mock，脱敏记录
        logger.warning("wx-login failed: %s", str(exc)[:120])
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("wx-login unexpected error")
        raise HTTPException(status_code=502, detail="微信服务暂不可用") from exc

    app_id = settings.wx_appid or "default"
    identity = (
        db.query(UserExternalIdentity)
        .filter_by(provider="wechat_miniprogram", app_id=app_id, subject_id=openid)
        .first()
    )
    if identity is not None:
        user = db.get(User, identity.user_id)
        if user is None or user.status != "active":
            raise HTTPException(status_code=403, detail="账号已被禁用")
        identity.last_login_at = datetime.now(timezone.utc)
        db.commit()
        token = create_access_token(user.id, user.role)
        # 审计：微信登录成功
        try:
            from app.services.student_case_service import audit

            # 用 student_case 锚点记录，case_id 为用户 id 以便追踪
            audit(db, user.id, "wx.login", "user", user.id, None, {"provider": "wechat_miniprogram"})
            db.commit()
        except Exception:  # noqa: BLE001
            pass
        return {"access_token": token, "user": UserOut.model_validate(user).model_dump()}

    # 未绑定
    ticket = _create_bind_ticket(openid, unionid)
    return {"bind_ticket": ticket, "bind_expires_in": 300}


@router.post("/wx-bind")
def wx_bind(body: WxBindRequest, db: Session = Depends(get_db)):
    """消费一次性 bind_ticket，绑定已有账号或通过邀请码注册后绑定。"""
    payload = _verify_bind_ticket(body.bind_ticket)
    openid = payload.get("openid")
    unionid = payload.get("unionid")
    app_id = payload.get("app_id") or (settings.wx_appid or "default")
    jti = payload.get("jti")

    if not openid:
        raise HTTPException(status_code=400, detail="bind_ticket 缺少 openid")

    # 唯一约束预检：该 openid 是否已被其他账号占用
    existing_identity = (
        db.query(UserExternalIdentity)
        .filter_by(provider="wechat_miniprogram", app_id=app_id, subject_id=openid)
        .first()
    )
    if existing_identity is not None:
        raise HTTPException(status_code=409, detail="该微信已绑定其他账号")

    user: User | None = None

    # 分支一：邀请码注册后绑定
    if body.invite_code:
        if not body.username or not body.password or not body.role:
            raise HTTPException(status_code=400, detail="邀请码注册需提供 username/password/role")
        if body.role not in (ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_CONSULTANT, ROLE_SUBJECT_TEACHER, ROLE_STUDENT, ROLE_PARENT):
            raise HTTPException(status_code=400, detail="仅支持注册班主任、德育主任、咨询老师、任课老师、学生或家长账号")
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=409, detail="用户名已存在")
        invite = (
            db.query(InviteCode)
            .filter(InviteCode.code == body.invite_code.strip())
            .with_for_update()
            .first()
        )
        if invite is None:
            raise HTTPException(status_code=400, detail="邀请码不存在")
        if invite.role != body.role:
            raise HTTPException(status_code=400, detail="邀请码角色与所选角色不匹配")
        if invite.status != INVITE_STATUS_ACTIVE:
            raise HTTPException(status_code=400, detail="邀请码已被使用或停用")
        if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="邀请码已过期")
        user = User(
            username=body.username,
            password_hash=hash_password(body.password),
            name=(body.name or body.username),
            role=body.role,
        )
        db.add(user)
        db.flush()
        invite.status = INVITE_STATUS_USED
        invite.used_by = user.id
        invite.used_at = datetime.now(timezone.utc)
    else:
        # 分支二：绑定已有账号
        if not body.username or not body.password:
            raise HTTPException(status_code=400, detail="请提供用户名与密码")
        user = db.query(User).filter(User.username == body.username).first()
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        if user.status != "active":
            raise HTTPException(status_code=403, detail="账号已被禁用")

    # 同一用户是否已绑定其他微信（按 uq_provider_user 约束，一用户一微信）
    dup_user_bind = (
        db.query(UserExternalIdentity)
        .filter_by(provider="wechat_miniprogram", user_id=user.id)
        .first()
    )
    if dup_user_bind is not None:
        raise HTTPException(status_code=409, detail="该账号已绑定其他微信")

    # 创建绑定（事务内）
    identity = UserExternalIdentity(
        user_id=user.id,
        provider="wechat_miniprogram",
        app_id=app_id,
        subject_id=openid,
        unionid=unionid,
        bound_at=datetime.now(timezone.utc),
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(identity)
    try:
        db.flush()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=409, detail="绑定冲突，请重试") from exc

    # 标记票据已消费（内存）
    _consume_jti(jti)

    try:
        from app.services.student_case_service import audit

        audit(db, user.id, "wx.bind", "user_external_identity", identity.id, None, {"provider": "wechat_miniprogram"})
    except Exception:  # noqa: BLE001
        pass
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "user": UserOut.model_validate(user).model_dump()}


@router.post("/wx-unbind")
def wx_unbind(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """解绑当前用户的微信身份。"""
    app_id = settings.wx_appid or "default"
    identity = (
        db.query(UserExternalIdentity)
        .filter_by(provider="wechat_miniprogram", user_id=user.id, app_id=app_id)
        .first()
    )
    # 兼容未指定 app_id 的历史绑定
    if identity is None:
        identity = db.query(UserExternalIdentity).filter_by(provider="wechat_miniprogram", user_id=user.id).first()
    if identity is None:
        raise HTTPException(status_code=404, detail="未绑定微信")
    db.delete(identity)
    try:
        from app.services.student_case_service import audit

        audit(db, user.id, "wx.unbind", "user_external_identity", identity.id, None, {"provider": "wechat_miniprogram"})
    except Exception:  # noqa: BLE001
        pass
    db.commit()
    return {"success": True}


@router.get("/me/children", response_model=list[ChildBrief])
def me_children(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """家长真实子女列表：含暂无可见总案的子女，最新可见档案摘要用于空态区分。"""
    if user.role != ROLE_PARENT:
        raise HTTPException(status_code=403, detail="仅家长可查看子女列表")
    links = db.query(StudentGuardian).filter_by(parent_id=user.id).all()
    if not links:
        return []
    # 批量拉取学生与班级信息
    student_ids = [link.student_id for link in links]
    students = {u.id: u for u in db.query(User).filter(User.id.in_(student_ids)).all()}
    # 关联的总案（按更新时间取最新一条，家长仅见 PARENT_VISIBLE_STATUSES 的在 _detail 中过滤，但此处摘要需展示状态以便区分空态）
    from app.services.student_case_service import PARENT_VISIBLE_STATUSES

    cases = db.query(StudentCase).filter(StudentCase.student_id.in_(student_ids)).order_by(StudentCase.updated_at.desc()).all()
    latest_by_student: dict[int, StudentCase] = {}
    for case in cases:
        if case.student_id not in latest_by_student:
            latest_by_student[case.student_id] = case

    result: list[ChildBrief] = []
    for link in links:
        stu = students.get(link.student_id)
        case = latest_by_student.get(link.student_id)
        # 取班级与周期名称（若有）
        class_name = None
        cycle_name = None
        if case is not None:
            from app.models.class_ import Class
            from app.models.student_case import CaseCycle

            cls = db.get(Class, case.class_id) if case.class_id else None
            if cls:
                class_name = cls.name
            cyc = db.get(CaseCycle, case.cycle_id) if case.cycle_id else None
            if cyc:
                cycle_name = cyc.name
        else:
            class_name = None
            cycle_name = None
        # 仅当总案可见时摘要才有意义，否则 latest_case_status 仍可反映草稿/待审等内部状态，但前端需按 PARENT_VISIBLE_STATUSES 判断是否可点击
        visible = case is not None and case.status in PARENT_VISIBLE_STATUSES
        result.append(
            ChildBrief(
                student_id=link.student_id,
                student_name=stu.name if stu else f"学生#{link.student_id}",
                class_id=case.class_id if case else None,
                class_name=class_name,
                cycle_name=cycle_name,
                latest_case_id=case.id if case else None,
                latest_case_status=case.status if case else None,
                latest_case_summary=(case.current_summary if visible and case else None),
                latest_case_version=case.version if visible and case else None,
            )
        )
    return result


@router.post("/register", response_model=UserOut)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """公开注册：班主任、德育主任、咨询老师、任课老师、学生或家长必须使用对应角色的邀请码。"""
    if body.role not in (ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_CONSULTANT, ROLE_SUBJECT_TEACHER, ROLE_STUDENT, ROLE_PARENT):
        raise HTTPException(status_code=400, detail="仅支持注册班主任、德育主任、咨询老师、任课老师、学生或家长账号")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")

    invite = (
        db.query(InviteCode)
        .filter(InviteCode.code == body.invite_code.strip())
        .with_for_update()
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=400, detail="邀请码不存在")
    if invite.role != body.role:
        raise HTTPException(status_code=400, detail="邀请码角色与所选角色不匹配")
    if invite.status != INVITE_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="邀请码已被使用或停用")
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="邀请码已过期")

    # 任课老师必须填写教授学科
    if body.role == ROLE_SUBJECT_TEACHER and not body.subject:
        raise HTTPException(status_code=400, detail="任课老师注册时必须填写教授学科")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
        subject=body.subject or "",
    )
    db.add(user)
    db.flush()

    invite.status = INVITE_STATUS_USED
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
