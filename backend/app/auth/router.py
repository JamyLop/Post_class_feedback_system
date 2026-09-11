"""认证路由：登录 / 当前用户 / 邀请码注册 / 微信小程序登录绑定。"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
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
from app.models.user import ROLE_ADMIN, ROLE_CONSULTANT, ROLE_DEYU_DIRECTOR, ROLE_PARENT, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.models.user_external_identity import ConsumedWxBindTicket, UserExternalIdentity
from app.schemas.admin import RegisterRequest
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.schemas.wx_auth import ChildBrief, WxBindRequest, WxLoginRequest
from app.services import captcha_service

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

# 除学生外，其他角色注册/绑定必须使用手机号作为用户名
import re as _re

PHONE_RE = _re.compile(r"^1[3-9]\d{9}$")


def _require_phone_username(role: str, username: str) -> str:
    """非学生角色用户名必须为11位手机号；返回 strip 后的用户名。"""
    cleaned = (username or "").strip()
    if role != ROLE_STUDENT and not PHONE_RE.fullmatch(cleaned):
        raise HTTPException(status_code=400, detail="除学生外，用户名必须为11位手机号")
    return cleaned

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
    if not jti:
        raise HTTPException(status_code=400, detail="bind_ticket 已使用或无效")
    return payload


def _check_captcha(captcha_id: str | None, captcha_code: str | None) -> None:
    """登录/注册共用：缺失或错误均 400，且错误时提示刷新。"""
    if not (captcha_id or "").strip() or not (captcha_code or "").strip():
        raise HTTPException(status_code=400, detail="请输入验证码")
    if not captcha_service.verify_captcha(captcha_id, captcha_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请刷新后重试")


def _validate_invite(invite: InviteCode | None, role: str) -> InviteCode:
    """校验邀请码可用：存在、角色匹配、未停用、未过期、未用满次数。"""
    if invite is None:
        raise HTTPException(status_code=400, detail="邀请码不存在")
    if invite.role != role:
        raise HTTPException(status_code=400, detail="邀请码角色与所选角色不匹配")
    max_uses = invite.max_uses or 1
    used_count = invite.used_count or 0
    if invite.status != INVITE_STATUS_ACTIVE or used_count >= max_uses:
        raise HTTPException(status_code=400, detail="邀请码已被使用或停用")
    if invite.expires_at is not None:
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="邀请码已过期")
    return invite


def _consume_invite(invite: InviteCode, user_id: int) -> None:
    """核销一次：计数+1；用满 max_uses 后才置为 used。"""
    invite.used_count = (invite.used_count or 0) + 1
    invite.used_by = user_id
    invite.used_at = datetime.now(timezone.utc)
    if invite.used_count >= (invite.max_uses or 1):
        invite.status = INVITE_STATUS_USED


@router.get("/captcha")
def get_captcha():
    """获取图形验证码：返回 captcha_id + base64 图片，前端登录/注册时回传 id 与用户输入。"""
    captcha_id, _code, image_b64 = captcha_service.create_captcha()
    return {
        "captcha_id": captcha_id,
        "image": f"data:image/png;base64,{image_b64}",
        "expires_in": captcha_service.EXPIRE_SECONDS,
    }


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """账号密码 + 图形验证码登录，签发 JWT。

    用户名兼容历史账号与新手机号账号：除学生学号外，其他角色注册已统一为11位手机号，
    此处不限制格式，仅 strip 后精确匹配，保证新老账号均可登录。
    """
    _check_captcha(body.captcha_id, body.captcha_code)
    username = (body.username or "").strip()
    user = db.query(User).filter(User.username == username).first()
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

    # 与绑定记录放在同一事务中，以 jti 主键的唯一约束跨进程原子地消费票据。
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    db.add(ConsumedWxBindTicket(jti=jti, expires_at=expires_at))
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="bind_ticket 已使用或无效") from exc

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
        if body.role not in (ROLE_ADMIN, ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_CONSULTANT, ROLE_SUBJECT_TEACHER, ROLE_STUDENT, ROLE_PARENT):
            raise HTTPException(status_code=400, detail="仅支持注册管理员、班主任、德育主任、咨询老师、任课老师、学生或家长账号")
        body.username = _require_phone_username(body.role, body.username)
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=409, detail="用户名已存在")
        invite = (
            db.query(InviteCode)
            .filter(InviteCode.code == body.invite_code.strip())
            .with_for_update()
            .first()
        )
        _validate_invite(invite, body.role)
        user = User(
            username=body.username,
            password_hash=hash_password(body.password),
            name=(body.name or body.username),
            role=body.role,
        )
        db.add(user)
        db.flush()
        _consume_invite(invite, user.id)
    else:
        # 分支二：绑定已有账号（兼容手机号与历史用户名，均 strip 后匹配）
        if not body.username or not body.password:
            raise HTTPException(status_code=400, detail="请提供用户名与密码")
        username = (body.username or "").strip()
        user = db.query(User).filter(User.username == username).first()
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
    """公开注册：邀请码 + 图形验证码，管理员、班主任、德育主任、咨询老师、任课老师、学生或家长必须使用对应角色的邀请码。

    除学生外，其他角色用户名必须为11位手机号。
    """
    _check_captcha(body.captcha_id, body.captcha_code)
    if body.role not in (ROLE_ADMIN, ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_CONSULTANT, ROLE_SUBJECT_TEACHER, ROLE_STUDENT, ROLE_PARENT):
        raise HTTPException(status_code=400, detail="仅支持注册管理员、班主任、德育主任、咨询老师、任课老师、学生或家长账号")
    body.username = _require_phone_username(body.role, body.username)
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")

    invite = (
        db.query(InviteCode)
        .filter(InviteCode.code == body.invite_code.strip())
        .with_for_update()
        .first()
    )
    _validate_invite(invite, body.role)

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

    _consume_invite(invite, user.id)
    db.commit()
    db.refresh(user)
    return user
