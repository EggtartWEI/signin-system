import os
import socket
import time
import logging
import binascii
import json
import re
import urllib.parse
import uuid
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any, List, Tuple

import requests
import uvicorn
from dotenv import load_dotenv
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services import whitelist_service

# --- 邮件配置（用于重置密码）---
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "2377083243@qq.com"
SMTP_PASSWORD = "pnepygwexuvpdjaf"

# --- 1. 初始化配置与日志 ---
# 加载 .env 文件，覆盖已存在的环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

def _get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
AUDIT_LOG_RETENTION_DAYS = _get_env_int("AUDIT_LOG_RETENTION_DAYS", 90)
APP_LOG_RETENTION_DAYS = _get_env_int("APP_LOG_RETENTION_DAYS", 30)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if origin.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX")
TRUST_PROXY_HEADERS = _get_env_bool("TRUST_PROXY_HEADERS", False)
REQUIRE_HTTPS = _get_env_bool("REQUIRE_HTTPS", False)
ENABLE_DOCS = _get_env_bool("ENABLE_DOCS", False)
MAX_BODY_SIZE = _get_env_int("MAX_BODY_SIZE", 10_000)
RATE_LIMIT_WINDOW_SECONDS = _get_env_int("RATE_LIMIT_WINDOW_SECONDS", 300)
RATE_LIMIT_MAX_ATTEMPTS = _get_env_int("RATE_LIMIT_MAX_ATTEMPTS", 5)
LOCKOUT_SECONDS = _get_env_int("LOCKOUT_SECONDS", 1800)
RETURN_HTML_CONTENT = _get_env_bool("RETURN_HTML_CONTENT", False)
PORTAL_CONNECT_TIMEOUT = _get_env_int("PORTAL_CONNECT_TIMEOUT", 5)
PORTAL_READ_TIMEOUT = _get_env_int("PORTAL_READ_TIMEOUT", 10)
REQUIRE_PORTAL_HTTPS = _get_env_bool("REQUIRE_PORTAL_HTTPS", True)
WHITELIST_ENABLED = _get_env_bool("WHITELIST_ENABLED", False)
# 调试输出
print(f"[DEBUG] WHITELIST_ENABLED raw value: {os.getenv('WHITELIST_ENABLED')}")
print(f"[DEBUG] WHITELIST_ENABLED parsed: {WHITELIST_ENABLED}")
WHITELIST_DB_PATH = os.getenv("WHITELIST_DB_PATH", "data/whitelist.db")

# 内存中的 session 存储（生产环境应使用 Redis 等）
_sessions = {}
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")

# 本地管理员账户配置（非OA账户）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_NAME = os.getenv("ADMIN_NAME", "系统管理员")
ADMIN_DEPARTMENT = os.getenv("ADMIN_DEPARTMENT", "管理部")

# 加载外委账号配置
EXTERNAL_USERS_FILE = os.path.join(os.path.dirname(__file__), 'external_users.json')
EXTERNAL_USERS = {}
try:
    if os.path.exists(EXTERNAL_USERS_FILE):
        with open(EXTERNAL_USERS_FILE, 'r', encoding='utf-8') as f:
            EXTERNAL_USERS = json.load(f)
        print(f"[INFO] 已加载 {len(EXTERNAL_USERS)} 个外委账号")
    else:
        print(f"[WARN] 外委账号配置文件不存在: {EXTERNAL_USERS_FILE}")
except Exception as e:
    print(f"[ERROR] 加载外委账号配置失败: {e}")

log_path = Path(LOG_DIR)
log_path.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("AttendanceLoginOnly")
logger.setLevel(LOG_LEVEL)
logger.handlers.clear()
logger.propagate = False

_log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
_app_handler = TimedRotatingFileHandler(
    log_path / "app.log",
    when="midnight",
    backupCount=APP_LOG_RETENTION_DAYS,
    encoding="utf-8",
)
_app_handler.setFormatter(_log_formatter)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_formatter)
logger.addHandler(_app_handler)
logger.addHandler(_console_handler)

audit_logger = logging.getLogger("AttendanceAudit")
audit_logger.setLevel("INFO")
audit_logger.handlers.clear()
audit_logger.propagate = False
_audit_handler = TimedRotatingFileHandler(
    log_path / "audit.log",
    when="midnight",
    backupCount=AUDIT_LOG_RETENTION_DAYS,
    encoding="utf-8",
)
_audit_handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(_audit_handler)

RSA_MODULUS_HEX = os.getenv("RSA_MODULUS_HEX")
RSA_EXPONENT = os.getenv("RSA_EXPONENT")
if RSA_MODULUS_HEX:
    RSA_MODULUS_HEX = RSA_MODULUS_HEX.strip()
if RSA_EXPONENT:
    RSA_EXPONENT = RSA_EXPONENT.strip()
RSA_CIPHERTEXT_HEX_LEN = len(RSA_MODULUS_HEX) if RSA_MODULUS_HEX else None
AWS_PORTAL_URL = os.getenv("AWS_PORTAL_URL")

required_env_vars = ["AWS_PORTAL_URL", "RSA_MODULUS_HEX", "RSA_EXPONENT"]
missing_vars = [v for v in required_env_vars if not os.getenv(v)]

if missing_vars:
    logger.error(f"⚠️ 缺少必需的环境变量: {', '.join(missing_vars)}")
if not RSA_MODULUS_HEX or not RSA_EXPONENT:
    logger.warning("⚠️ RSA公钥配置缺失，登录功能可能不可用")
if AWS_PORTAL_URL and REQUIRE_PORTAL_HTTPS and not AWS_PORTAL_URL.lower().startswith("https://"):
    logger.error("⚠️ AWS_PORTAL_URL 未使用 HTTPS，生产环境不符合等保二级要求")
if WHITELIST_ENABLED and not ADMIN_API_TOKEN:
    logger.warning("⚠️ 启用了白名单但未配置 ADMIN_API_TOKEN，管理员接口不可用")

if WHITELIST_ENABLED:
    try:
        whitelist_service.ensure_db_ready()
    except Exception:
        logger.exception("⚠️ 白名单数据库初始化失败")

# --- 2. 登录逻辑 ---
class RateLimiter:
    def __init__(self, window_seconds: int, max_attempts: int, lockout_seconds: int) -> None:
        self.window_seconds = window_seconds
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts: Dict[str, List[float]] = {}
        self._locked_until: Dict[str, float] = {}
        self._lock = Lock()

    def is_locked(self, key: str) -> Tuple[bool, int]:
        with self._lock:
            until = self._locked_until.get(key, 0)
            now = time.time()
            if until > now:
                return True, int(until - now)
            return False, 0

    def register_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            attempts = self._attempts.get(key, [])
            attempts = [ts for ts in attempts if now - ts <= self.window_seconds]
            attempts.append(now)
            if len(attempts) >= self.max_attempts:
                self._locked_until[key] = now + self.lockout_seconds
                self._attempts.pop(key, None)
            else:
                self._attempts[key] = attempts

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._locked_until.pop(key, None)

rate_limiter = RateLimiter(
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    max_attempts=RATE_LIMIT_MAX_ATTEMPTS,
    lockout_seconds=LOCKOUT_SECONDS,
)


class WhitelistUserCreate(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    enabled: bool = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sanitize_username(username: str) -> str:
    return re.sub(r"[^\w@\.-]", "", username)

def _mask_user(user: str) -> str:
    if len(user) <= 2:
        return "*" * len(user)
    return f"{user[:1]}***{user[-1:]}"

def _is_encrypted_password(value: str) -> bool:
    if not value or not RSA_CIPHERTEXT_HEX_LEN:
        return False
    if len(value) != RSA_CIPHERTEXT_HEX_LEN:
        return False
    return re.fullmatch(r"[0-9a-fA-F]+", value) is not None

def _get_client_ip(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

def _is_https_request(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    if TRUST_PROXY_HEADERS:
        proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
        return proto == "https"
    return False

def _origin_from_referer(referer: str) -> Optional[str]:
    if not referer:
        return None
    parsed = urllib.parse.urlparse(referer)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None

def _is_origin_allowed(origin: Optional[str]) -> bool:
    if not origin:
        return True
    if origin in ALLOWED_ORIGINS:
        return True
    if ALLOWED_ORIGIN_REGEX:
        try:
            return re.match(ALLOWED_ORIGIN_REGEX, origin) is not None
        except re.error:
            logger.error("ALLOWED_ORIGIN_REGEX 配置无效")
    return False

def _emit_audit_event(
    event_type: str,
    request: Optional[Request] = None,
    username: Optional[str] = None,
    result: Optional[str] = None,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "timestamp": _utc_now(),
        "event_type": event_type,
    }
    if request:
        payload.update(
            {
                "request_id": getattr(request.state, "request_id", None),
                "ip_address": _get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
            }
        )
    if username:
        payload["user_id"] = _sanitize_username(username)
    if result:
        payload["result"] = result
    if reason:
        payload["reason"] = reason
    if extra:
        payload.update(extra)
    audit_logger.info(json.dumps(payload, ensure_ascii=False))


def _get_admin_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    token = request.headers.get("x-admin-token")
    return token.strip() if token else None


def _require_admin(request: Request) -> None:
    token = _get_admin_token(request)
    if not ADMIN_API_TOKEN:
        raise HTTPException(500, "管理员接口未配置")
    if token != ADMIN_API_TOKEN:
        _emit_audit_event(
            "admin_auth_failed",
            request=request,
            result="blocked",
            reason="invalid_token",
        )
        raise HTTPException(401, "未授权")

def encrypt_password(password: str) -> str:
    if not RSA_MODULUS_HEX or not RSA_EXPONENT:
        raise ValueError("RSA 配置缺失")
    n = int(RSA_MODULUS_HEX, 16)
    e = int(RSA_EXPONENT)
    key = RSA.construct((n, e))
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(password.encode('utf-8'))
    return binascii.hexlify(encrypted).decode('utf-8')

def create_session() -> requests.Session:
    """创建一个新的 Session 对象"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 Attendance-Login/1.0',
        'Accept': 'application/json, */*',
    })
    return session

def parse_html(html_content: str) -> Dict[str, Any]:
    """解析HTML页面，提取用户ID、姓名、部门信息"""
    result = {}
    
    try:
        # 提取用户ID：从JavaScript变量中匹配 var uid = "12061413";
        id_match = re.search(r'var\s+uid\s*=\s*["\'](\d+)["\']', html_content)
        if id_match:
            result['id'] = id_match.group(1)
        
        # 提取用户ID：如果上面没找到，再尝试匹配 "用户ID: 12061413" 格式
        if not result.get('id'):
            id_match = re.search(r'用户ID[:\s]+(\d+)', html_content)
            if id_match:
                result['id'] = id_match.group(1)
        
        # 提取姓名：从特定HTML元素中匹配 <span id="userInfoName" class="user-info-name">李茗</span>
        name_match = re.search(r'<span[^>]*id="userInfoName"[^>]*class="[^"]*user-info-name[^"]*"[^>]*>([^<]*)</span>', html_content)
        if name_match:
            result['name'] = name_match.group(1).strip()
        
        # 提取姓名：如果上面没找到，再尝试匹配 "用户姓名: 李茗" 格式
        if not result.get('name'):
            name_match = re.search(r'用户姓名[:\s]+([^\s<>\n]+)', html_content)
            if name_match:
                result['name'] = name_match.group(1)
        
        # 提取部门：从特定HTML元素中匹配 <span id="userInfoDept" class="user-info-dept">人工智能工作室</span>
        dept_match = re.search(r'<span[^>]*id="userInfoDept"[^>]*class="[^"]*user-info-dept[^"]*"[^>]*>([^<]*)</span>', html_content)
        if dept_match:
            result['department'] = dept_match.group(1).strip()
        
        # 提取部门：如果上面没找到，再尝试匹配 "部门: 人工智能工作室" 格式
        if not result.get('department'):
            dept_match = re.search(r'部门[:\s]+([^\s<>\n]+(?:\s+[^\s<>\n]+)*)', html_content)
            if dept_match:
                result['department'] = dept_match.group(1)
        
        # 如果找到了任何信息，仅在调试级别记录
        if result and logger.isEnabledFor(logging.DEBUG):
            logger.debug("=" * 50)
            logger.debug("用户信息解析结果:")
            logger.debug("=" * 50)
            if 'id' in result:
                logger.debug(f"用户ID: {result['id']}")
            if 'name' in result:
                logger.debug(f"用户姓名: {result['name']}")
            if 'department' in result:
                logger.debug(f"部门: {result['department']}")
            logger.debug("=" * 50)
    except Exception as e:
        logger.warning(f"HTML解析失败: {e}")
    
    return result

def do_login(
    username: str,
    password: str,
    password_is_encrypted: bool = False,
) -> tuple[bool, str, Optional[str], Optional[str]]:
    login_api = f"{AWS_PORTAL_URL}/portal/r/jd"
    login_page = f"{AWS_PORTAL_URL}/portal/"
    target_page = f"{AWS_PORTAL_URL}/portal/r/w"

    try:
        encrypted_pwd = password if password_is_encrypted else encrypt_password(password)
        payload = {
            'userid': username, 'pwd': encrypted_pwd,
            'rememberMePwd': 'on', 'lang': 'cn',
            'cmd': 'CLIENT_USER_LOGIN', 'sid': '', 'deviceType': 'pc',
            '_CACHE_LOGIN_TIME_': str(int(time.time() * 1000)),
            'pwdEncode': 'RSA', 'timeZone': '8',
            'loginUrl': urllib.parse.quote(login_page)
        }

        resp = create_session().post(
            login_api,
            data=payload,
            headers={'Referer': login_page},
            timeout=(PORTAL_CONNECT_TIMEOUT, PORTAL_READ_TIMEOUT),
        )
        if resp.status_code != 200:
            logger.warning(f"登录请求失败: HTTP {resp.status_code}")
            return False, "登录服务暂时不可用，请稍后重试", None, None

        result = resp.json()
        if result.get('data', {}).get('sid'):
            sid = result['data']['sid']
            # 获取登录后的 /portal/r/w 页面内容，使用POST请求
            page_payload = {
                'userid': username,
                'pwd': encrypted_pwd,
                'rememberMePwd': 'on',
                'lang': 'cn',
                'cmd': 'CLIENT_USER_HOME',
                'sid': sid,
                'deviceType': 'pc',
                '_CACHE_LOGIN_TIME_': str(int(time.time() * 1000))
            }
            page_resp = create_session().post(
                target_page,
                data=page_payload,
                headers={'Referer': login_page},
                timeout=(PORTAL_CONNECT_TIMEOUT, PORTAL_READ_TIMEOUT),
            )
            html_content = page_resp.text if page_resp.status_code == 200 else None
            logger.info(f"登录成功: {_mask_user(username)}")
            return True, "登录成功", sid, html_content
        return False, result.get('msg', '未知错误'), None, None
    except Exception as e:
        logger.exception("登录请求失败")
        return False, str(e), None, None

# --- 4. FastAPI 应用 ---
app = FastAPI(
    title="考勤登录服务",
    version="1.1",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

if ALLOWED_ORIGINS or ALLOWED_ORIGIN_REGEX:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=ALLOWED_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id

    if REQUIRE_HTTPS and not _is_https_request(request):
        return JSONResponse(
            status_code=400,
            content={"detail": "仅允许 HTTPS 访问"},
        )

    content_length = request.headers.get("content-length")
    if content_length and MAX_BODY_SIZE:
        try:
            if int(content_length) > MAX_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "请求体过大"},
                )
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "无效的 Content-Length"},
            )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "base-uri 'self'; frame-ancestors 'none'",
    )
    if REQUIRE_HTTPS:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("Cache-Control", "no-store")
    return response

@app.post("/api/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_encrypted: Optional[str] = Form(None),
):
    client_ip = _get_client_ip(request)
    origin = request.headers.get("origin") or _origin_from_referer(request.headers.get("referer", ""))
    if origin and not _is_origin_allowed(origin):
        _emit_audit_event(
            "login_rejected",
            request=request,
            username=username,
            result="blocked",
            reason="origin_not_allowed",
        )
        raise HTTPException(403, "非法来源")

    username = username.strip()
    password = password.strip()
    password_is_encrypted = _is_encrypted_password(password)
    if password_encrypted:
        password_is_encrypted = True
        if not _is_encrypted_password(password):
            _emit_audit_event(
                "login_rejected",
                request=request,
                username=username,
                result="blocked",
                reason="invalid_encrypted_password",
            )
            raise HTTPException(400, "密码加密格式不正确")
    if not username or not password:
        _emit_audit_event(
            "login_rejected",
            request=request,
            username=username,
            result="blocked",
            reason="empty_credentials",
        )
        raise HTTPException(400, "用户名或密码不能为空")

    if len(username) > 64 or (not password_is_encrypted and len(password) > 128):
        _emit_audit_event(
            "login_rejected",
            request=request,
            username=username,
            result="blocked",
            reason="credential_too_long",
        )
        raise HTTPException(400, "用户名或密码格式不正确")

    if not re.match(r"^[A-Za-z0-9_.@-]+$", username):
        _emit_audit_event(
            "login_rejected",
            request=request,
            username=username,
            result="blocked",
            reason="invalid_username_format",
        )
        raise HTTPException(400, "用户名格式不正确")

    limiter_key = f"{client_ip}:{username}"
    locked, remaining = rate_limiter.is_locked(limiter_key)
    if locked:
        _emit_audit_event(
            "login_blocked",
            request=request,
            username=username,
            result="blocked",
            reason="rate_limited",
            extra={"retry_after_seconds": remaining},
        )
        raise HTTPException(429, "登录失败次数过多，请稍后再试")

    # 先检查是否是本地管理员账户
    is_admin = False
    if username == ADMIN_USERNAME:
        # 验证管理员密码（现在前端对管理员使用明文传输）
        if password == ADMIN_PASSWORD:
            is_admin = True
            # 生成管理员 session
            sid = str(uuid.uuid4())
            _sessions[sid] = {
                "id": ADMIN_USERNAME,
                "name": ADMIN_NAME,
                "department": ADMIN_DEPARTMENT,
                "is_admin": True,
                "login_time": _utc_now(),
            }
            _emit_audit_event(
                "login_success",
                request=request,
                username=username,
                result="success",
                extra={"is_admin": True},
            )
            return {
                "status": "success",
                "username": ADMIN_USERNAME,
                "sid": sid,
                "user_info": {
                    "id": ADMIN_USERNAME,
                    "name": ADMIN_NAME,
                    "department": ADMIN_DEPARTMENT,
                    "is_admin": True,
                },
            }
        else:
            _emit_audit_event(
                "login_failure",
                request=request,
                username=username,
                result="failure",
                reason="invalid_admin_password",
            )
            raise HTTPException(401, "管理员密码错误")

    # 检查是否是外委账号
    if username in EXTERNAL_USERS:
        external_user = EXTERNAL_USERS[username]
        # 验证外委账号密码
        if password == external_user["password"]:
            # 生成外委用户 session
            sid = str(uuid.uuid4())
            _sessions[sid] = {
                "id": username,
                "name": external_user["name"],
                "department": f"{external_user['dept_category']}-{external_user['dept_subitem']}",
                "dept_category": external_user["dept_category"],
                "dept_subitem": external_user["dept_subitem"],
                "is_external": True,
                "is_admin": False,
                "login_time": _utc_now(),
            }
            _emit_audit_event(
                "login_success",
                request=request,
                username=username,
                result="success",
                extra={"is_external": True},
            )
            return {
                "status": "success",
                "username": username,
                "sid": sid,
                "user_info": {
                    "id": username,
                    "name": external_user["name"],
                    "department": f"{external_user['dept_category']}-{external_user['dept_subitem']}",
                    "dept_category": external_user["dept_category"],
                    "dept_subitem": external_user["dept_subitem"],
                    "is_external": True,
                    "is_admin": False,
                },
            }
        else:
            _emit_audit_event(
                "login_failure",
                request=request,
                username=username,
                result="failure",
                reason="invalid_external_password",
            )
            raise HTTPException(401, "外委账号密码错误")

    # 非本地账号，走OA系统登录
    ok, msg, sid, html_content = do_login(username, password, password_is_encrypted)
    if not ok:
        service_error = msg == "登录服务暂时不可用，请稍后重试" or "timed out" in msg.lower()
        if service_error:
            _emit_audit_event(
                "login_failure",
                request=request,
                username=username,
                result="failure",
                reason="service_unavailable",
            )
            logger.warning(f"登录服务不可用: user={_mask_user(username)} ip={client_ip}")
            raise HTTPException(503, "登录服务暂时不可用，请稍后重试")

        rate_limiter.register_failure(limiter_key)
        _emit_audit_event(
            "login_failure",
            request=request,
            username=username,
            result="failure",
            reason="invalid_credentials",
        )
        logger.warning(f"登录失败: user={_mask_user(username)} ip={client_ip}")
        raise HTTPException(401, "用户名或密码错误")

    rate_limiter.reset(limiter_key)

    # 解析HTML页面，提取用户信息
    user_info = {}
    if html_content:
        user_info = parse_html(html_content)

    # 用户ID就是登录名，直接使用输入的username
    user_info["id"] = username

    user_name = user_info.get("name")
    print(f"[DEBUG] Checking whitelist: WHITELIST_ENABLED={WHITELIST_ENABLED}, type={type(WHITELIST_ENABLED)}")
    if WHITELIST_ENABLED:
        print(f"[DEBUG] Entering whitelist check block")
        try:
            allowed, matched_by = whitelist_service.is_user_allowed(username, user_name)
        except Exception:
            _emit_audit_event(
                "whitelist_error",
                request=request,
                username=username,
                result="failure",
                reason="whitelist_unavailable",
            )
            logger.exception("白名单服务不可用")
            raise HTTPException(503, "白名单服务暂时不可用，请稍后重试")

        if not allowed:
            admin_contact = whitelist_service.get_admin_contact()
            _emit_audit_event(
                "login_rejected",
                request=request,
                username=username,
                result="blocked",
                reason="whitelist_denied",
                extra={"user_name": user_name, "matched_by": matched_by},
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "账号未在白名单内，请联系管理员",
                    "admin_contact": admin_contact,
                },
            )

        _emit_audit_event(
            "whitelist_allowed",
            request=request,
            username=username,
            result="success",
            extra={"user_name": user_name, "matched_by": matched_by},
        )

    _emit_audit_event(
        "login_success",
        request=request,
        username=username,
        result="success",
    )

    # 保存 session 到内存存储
    _sessions[sid] = {
        "id": username,
        "name": user_name or username,
        "department": user_info.get("department", ""),
        "is_admin": False,  # 普通用户
        "login_time": _utc_now(),
    }

    # 在 user_info 中也添加 is_admin 字段
    user_info["is_admin"] = False

    response_payload = {
        "status": "success",
        "username": username,
        "sid": sid,
        "user_info": user_info,
    }
    if RETURN_HTML_CONTENT:
        response_payload["html_content"] = html_content
    return response_payload


@app.post("/api/admin/whitelist/users")
async def add_whitelist_user(request: Request, payload: WhitelistUserCreate):
    _require_admin(request)
    try:
        record = whitelist_service.upsert_allowed_user(
            user_id=payload.user_id,
            user_name=payload.user_name,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    _emit_audit_event(
        "whitelist_admin_upsert",
        request=request,
        username=payload.user_id or payload.user_name,
        result="success",
        extra={
            "user_id": record.user_id,
            "user_name": record.user_name,
            "enabled": record.enabled,
        },
    )
    return {
        "status": "ok",
        "user": {
            "user_id": record.user_id,
            "user_name": record.user_name,
            "enabled": record.enabled,
        },
    }


@app.get("/api/admin/whitelist/users")
async def list_whitelist_users(request: Request, limit: int = 200):
    _require_admin(request)
    users = whitelist_service.list_allowed_users(limit=limit)
    return {
        "status": "ok",
        "count": len(users),
        "items": users,
    }


@app.get("/api/admin/contact")
async def get_admin_contact():
    return whitelist_service.get_admin_contact()

@app.get("/api/auth/me")
async def auth_me(request: Request):
    """验证 token 并返回用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header[7:]  # 去掉 "Bearer " 前缀
    
    # 从 session 存储中查找用户信息
    user_info = _sessions.get(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    
    return user_info


def send_reset_email(to_email: str, username: str, new_password: str) -> bool:
    """发送重置密码邮件"""
    try:
        msg = MIMEText(f"""
尊敬的用户您好！

您的外委账号密码已重置：
账号：{username}
新密码：{new_password}

请使用新密码登录系统，登录后建议及时修改密码。

此邮件由系统自动发送，请勿回复。
        """, 'plain', 'utf-8')
        
        msg['From'] = Header(SMTP_USER, 'utf-8')
        msg['To'] = Header(to_email, 'utf-8')
        msg['Subject'] = Header('外委账号密码重置通知', 'utf-8')
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        
        logger.info(f"重置密码邮件已发送至 {to_email}")
        return True
    except Exception as e:
        logger.error(f"发送重置密码邮件失败: {e}")
        return False


def generate_random_password(length: int = 8) -> str:
    """生成随机密码"""
    # 包含大小写字母和数字
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def save_external_users():
    """保存外委账号到文件"""
    try:
        with open(EXTERNAL_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(EXTERNAL_USERS, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存外委账号失败: {e}")
        return False


@app.post("/api/external/change-password")
async def change_external_password(
    username: str = Form(...),
    old_password: str = Form(...),
    new_password: str = Form(...),
):
    """外委账号修改密码"""
    # 检查账号是否存在
    if username not in EXTERNAL_USERS:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    user = EXTERNAL_USERS[username]
    
    # 验证原密码
    if user.get('password') != old_password:
        raise HTTPException(status_code=401, detail="原密码错误")
    
    # 验证新密码长度
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于6位")
    
    # 修改密码
    user['password'] = new_password
    
    if save_external_users():
        logger.info(f"外委账号 {username} 修改密码成功")
        return {"success": True, "message": "密码修改成功"}
    else:
        raise HTTPException(status_code=500, detail="保存密码失败")


@app.post("/api/external/reset-password")
async def reset_external_password(
    username: str = Form(...),
    email: str = Form(...),
):
    """外委账号重置密码（发送随机密码到邮箱）"""
    # 检查账号是否存在
    if username not in EXTERNAL_USERS:
        # 为了安全，不暴露账号是否存在
        return {"success": True, "message": "如果账号存在，重置密码邮件已发送"}
    
    # 生成随机密码
    new_password = generate_random_password(8)
    
    # 更新密码
    EXTERNAL_USERS[username]['password'] = new_password
    
    if not save_external_users():
        raise HTTPException(status_code=500, detail="保存密码失败")
    
    # 发送邮件
    email_sent = send_reset_email(email, username, new_password)
    
    if email_sent:
        logger.info(f"外委账号 {username} 重置密码邮件已发送至 {email}")
        return {"success": True, "message": "重置密码邮件已发送，请查收"}
    else:
        # 邮件发送失败，恢复旧密码
        logger.error(f"外委账号 {username} 重置密码邮件发送失败")
        raise HTTPException(status_code=500, detail="邮件发送失败，请稍后重试")


@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    # 从外部文件读取登录页面HTML
    login_html_file = os.path.join(os.path.dirname(__file__), 'login_page.html')
    try:
        with open(login_html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        logger.error(f"读取登录页面失败: {e}")
        # 如果读取失败，返回错误信息
        return HTMLResponse(content="<h1>登录页面加载失败</h1><p>请联系管理员</p>", status_code=500)
    
    # 替换模板变量
    html = html.replace('"__RSA_MODULUS_HEX__"', json.dumps(RSA_MODULUS_HEX or ""))
    html = html.replace('"__RSA_EXPONENT__"', json.dumps(RSA_EXPONENT or "65537"))
    html = html.replace('__WHITELIST_ENABLED__', 'true' if WHITELIST_ENABLED else 'false')
    
    return HTMLResponse(content=html)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "time": _utc_now(),
    }

@app.get("/api/status")
async def api_status():
    return {
        "status": "ok",
        "time": _utc_now(),
    }

def find_available_port(start_port=8001, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"无法找到可用端口（{start_port}-{start_port + max_attempts}）")

if __name__ == "__main__":
    # 固定使用 8001 端口，确保与签到系统配置一致
    port = 8001
    print(f"""
{'='*50}
  🚀 考勤登录服务
{'='*50}
  🌐 登录页面:   http://localhost:{port}
  📡 API状态:   http://localhost:{port}/api/status
{'='*50}
""")
    uvicorn.run(app, host="0.0.0.0", port=port)
