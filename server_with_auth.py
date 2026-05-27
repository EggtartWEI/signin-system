#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
南宁公司值班签到系统 - 带登录保护版本
兼容 Python 2 和 Python 3
"""

from __future__ import print_function
import sys
import os
import json
import datetime
import re

# 根据Python版本导入不同模块
if sys.version_info[0] >= 3:
    # Python 3
    import http.server as BaseHTTPServer
    import socketserver
    from urllib.parse import urlparse, parse_qs, quote, unquote
    from urllib.request import urlopen
else:
    # Python 2
    import BaseHTTPServer
    import SocketServer as socketserver
    from urlparse import urlparse, parse_qs
    from urllib import quote, unquote
    from urllib2 import urlopen

# 配置
PORT = 3000

# 获取本机IP地址（用于构建访问URL）
def get_server_ip():
    """获取服务器IP地址"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

SERVER_IP = get_server_ip()

# 认证服务URL（默认使用本机IP，支持通过环境变量覆盖）
# 如果认证服务在其他机器上，请设置环境变量 AUTH_SERVICE_URL
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://%s:8001" % SERVER_IP)
DATA_FILE = 'data.json'
MODE_FILE = 'mode.json'
SESSION_COOKIE_NAME = 'signin_session'

# 功能开关
# ENABLE_IP_RESTRICTION: 是否启用IP限制（一天内同一IP只能签到一个部门）
# True = 启用限制, False = 禁用限制
ENABLE_IP_RESTRICTION = True

# 自动同步到云文档开关
# ENABLE_AUTO_SYNC: 是否在签到后自动同步到云文档
# True = 启用自动同步, False = 禁用自动同步
ENABLE_AUTO_SYNC = True

# 签到时间配置（工作日和周末不同）
# 只有开发者可以修改代码中的这些默认值
SIGNIN_SCHEDULE = {
    'weekday': {  # 周一到周五
        'evening': {
            'start': '17:30',      # 开始时间
            'end': '20:00',        # 正常结束时间（之后算迟到）
            'label': '晚上签到'
        }
    },
    'weekend': {  # 周六周日
        'morning': {
            'start': '07:00',
            'end': '09:00',
            'label': '早上签到'
        },
        'evening': {
            'start': '17:30',
            'end': '20:00',
            'label': '晚上签到'
        }
    }
}


def read_config():
    """读取配置文件"""
    config_file = 'config.json'
    default_config = {
        'enable_time_limit': True  # 是否启用时间限制（管理员可修改）
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
    except Exception as e:
        print("读取配置文件失败: " + str(e))
    
    return default_config


def save_config(config):
    """保存配置文件"""
    config_file = 'config.json'
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("保存配置文件失败: " + str(e))
        return False


def get_current_period():
    """获取当前签到时段信息
    
    返回:
        {
            'day_type': 'weekday'|'weekend',
            'period': 'morning'|'evening'|None,
            'period_name': str,
            'is_late': bool,
            'can_signin': bool,
            'message': str
        }
    """
    now = datetime.datetime.now()
    weekday = now.weekday()  # 0=周一, 5=周六, 6=周日
    current_time = now.hour * 60 + now.minute  # 当前时间（分钟）
    
    # 判断是工作日还是周末
    if weekday < 5:  # 周一到周五
        day_type = 'weekday'
        schedule = SIGNIN_SCHEDULE['weekday']
        # 工作日只有晚上签到
        period_info = schedule.get('evening')
        period = 'evening'
    else:  # 周六周日
        day_type = 'weekend'
        schedule = SIGNIN_SCHEDULE['weekend']
        # 周末根据时间判断是早上还是晚上（12点为界）
        if now.hour < 12:
            period_info = schedule.get('morning')
            period = 'morning'
        else:
            period_info = schedule.get('evening')
            period = 'evening'
    
    if not period_info:
        return {
            'day_type': day_type,
            'period': None,
            'period_name': '非签到时段',
            'is_late': False,
            'can_signin': True,
            'message': ''
        }
    
    # 解析时间
    start_h, start_m = map(int, period_info['start'].split(':'))
    end_h, end_m = map(int, period_info['end'].split(':'))
    start_time = start_h * 60 + start_m
    end_time = end_h * 60 + end_m
    
    # 判断是否早于开始时间
    if current_time < start_time:
        return {
            'day_type': day_type,
            'period': period,
            'period_name': period_info['label'],
            'is_late': False,
            'can_signin': False,
            'message': '未到签到时间，请不要提前签到'
        }
    
    # 判断是否晚于正常结束时间（算迟到）
    is_late = current_time > end_time
    
    return {
        'day_type': day_type,
        'period': period,
        'period_name': period_info['label'],
        'is_late': is_late,
        'can_signin': True,
        'message': ''
    }


def check_signin_time():
    """检查当前是否允许签到（兼容旧接口）
    
    返回:
        (bool, str): (是否允许签到, 提示信息)
    """
    config = read_config()
    
    # 如果不启用时间限制，直接允许
    if not config.get('enable_time_limit', True):
        return True, ""
    
    period_info = get_current_period()
    
    if not period_info['can_signin']:
        return False, period_info['message']
    
    return True, ""

# 导入同步模块（放在后面导入避免循环依赖）
def sync_to_kdocs():
    """同步当天数据到云文档"""
    if not ENABLE_AUTO_SYNC:
        return
    
    try:
        # 动态导入避免循环依赖
        import importlib.util
        sync_module_path = os.path.join(os.path.dirname(__file__), 'kdocs_sync', 'sync_module.py')
        
        if sys.version_info[0] >= 3 and sys.version_info[1] >= 5:
            # Python 3.5+
            spec = importlib.util.spec_from_file_location("sync_module", sync_module_path)
            sync_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_module)
        else:
            # Python 2 / Python 3.4-
            import imp
            sync_module = imp.load_source("sync_module", sync_module_path)
        
        # 执行同步
        success, message = sync_module.sync_today_data()
        if success:
            print("[自动同步] %s" % message)
        else:
            print("[自动同步] 失败: %s" % message)
            
    except Exception as e:
        print("[自动同步] 错误: %s" % str(e))

# 部门结构定义（与前端保持一致）
DEPT_STRUCTURE = {
    '公司值班': ['公司领导', '公司中层', '公司干部'],
    '计划部': ['库管'],
    '运行部': ['管理'],
    'D标': ['北京腾疆'],
    '生产管理': [
        '管理', 
        '汽机', 
        '锅炉', 
        '输煤环保', 
        {'name': '电气专业', 'slots': 2}, 
        {'name': '热控专业', 'slots': 2}
    ],
    'A标': ['管理', '汽机', '锅炉', '电气', '热控', '输煤', '硫硝'],
    '其他': ['起重维护', '保安', '保洁']
}

# MIME类型映射
MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}

# 简单的 session 存储
# session 格式: {session_id: {'user': user_info, 'created_at': timestamp, 'last_activity': timestamp}}
sessions = {}

# Session 超时时间（30分钟，单位：秒）
SESSION_TIMEOUT = 30 * 60


def clean_expired_sessions():
    """清理过期的 session"""
    now = datetime.datetime.now()
    expired_sessions = []
    
    for session_id, session_data in sessions.items():
        last_activity = session_data.get('last_activity')
        if last_activity:
            # 计算不活跃时间
            inactive_time = (now - last_activity).total_seconds()
            if inactive_time > SESSION_TIMEOUT:
                expired_sessions.append(session_id)
    
    # 删除过期 session
    for session_id in expired_sessions:
        del sessions[session_id]
        print("[会话管理] 清理过期 session: %s" % session_id[:8])


def update_session_activity(session_id):
    """更新 session 的最后活动时间"""
    if session_id in sessions:
        sessions[session_id]['last_activity'] = datetime.datetime.now()


def init_data_files():
    """初始化数据文件"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(MODE_FILE):
        with open(MODE_FILE, 'w') as f:
            json.dump({'mode': 'open', 'allowedIPs': []}, f)


def generate_default_records(date):
    """生成某天的默认空签到记录"""
    records = []
    for category, items in DEPT_STRUCTURE.items():
        for item in items:
            if isinstance(item, dict):
                # 多签到位置
                for i in range(item['slots']):
                    dept_name = item['name'] if i == 0 else '{}({})'.format(item['name'], i + 1)
                    full_dept = '{}-{}'.format(category, item['name'])
                    records.append({
                        'department': full_dept,
                        'displayName': dept_name,
                        'name': '-',
                        'employeeId': '-',
                        'phone': '-',
                        'signInTime': None,
                        'latitude': '',
                        'longitude': '',
                        'location': '',
                        'ip': '',
                        'isDefault': True
                    })
            else:
                full_dept = '{}-{}'.format(category, item)
                records.append({
                    'department': full_dept,
                    'displayName': item,
                    'name': '-',
                    'employeeId': '-',
                    'phone': '-',
                    'signInTime': None,
                    'latitude': '',
                    'longitude': '',
                    'location': '',
                    'ip': '',
                    'isDefault': True
                })
    return records


def get_or_create_daily_records(date):
    """获取或创建某天的签到记录"""
    data = read_data()
    if date not in data:
        # 生成默认空记录
        data[date] = generate_default_records(date)
        save_data(data)
    return data[date]


def read_data():
    """读取签到数据（带重试机制）"""
    max_retries = 5
    for retry in range(max_retries):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (IOError, OSError):
            # 文件被占用，等待后重试
            if retry < max_retries - 1:
                import time
                time.sleep(0.1 * (retry + 1))
                continue
            return {}
        except:
            return {}
    return {}


def save_data(data):
    """
    保存签到数据（原子写操作，防止并发覆盖）
    使用临时文件+重命名的方式确保原子性
    """
    temp_file = DATA_FILE + '.tmp'
    max_retries = 5
    
    for retry in range(max_retries):
        try:
            # 写入临时文件
            with open(temp_file, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子重命名
            if os.path.exists(DATA_FILE):
                os.replace(temp_file, DATA_FILE)
            else:
                os.rename(temp_file, DATA_FILE)
            
            return True
            
        except (IOError, OSError):
            # 如果被占用，等待后重试
            if retry < max_retries - 1:
                import time
                time.sleep(0.1 * (retry + 1))
                continue
            raise
    
    return False


def read_mode():
    """读取模式设置"""
    try:
        with open(MODE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'mode': 'open', 'allowedIPs': []}


def get_session_from_cookie(headers):
    """从请求头中获取 session cookie"""
    cookie_header = headers.get('Cookie', '')
    if not cookie_header:
        return None
    
    # 解析 cookie
    cookies = {}
    for cookie in cookie_header.split(';'):
        if '=' in cookie:
            name, value = cookie.strip().split('=', 1)
            cookies[name] = value
    
    return cookies.get(SESSION_COOKIE_NAME)


def verify_token_with_auth_service(token):
    """调用认证服务验证 token"""
    try:
        import requests
        headers = {"Authorization": "Bearer " + token}
        response = requests.get(
            AUTH_SERVICE_URL + "/api/auth/me",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return {
                "valid": True,
                "user": response.json()
            }
        else:
            return {
                "valid": False,
                "error": "Token 无效或已过期"
            }
    except Exception as e:
        # 如果认证服务不可用，允许访问（降级处理）
        print("认证服务不可用: " + str(e))
        return {
            "valid": True,
            "user": {"name": "未知用户", "department": "未知部门"}
        }


def is_logged_in(headers):
    """检查用户是否已登录"""
    session_token = get_session_from_cookie(headers)
    if not session_token:
        return False, None
    
    # 清理过期 session
    clean_expired_sessions()
    
    # 检查 session 是否有效
    if session_token in sessions:
        session_data = sessions[session_token]
        # 更新最后活动时间
        update_session_activity(session_token)
        # 返回用户信息
        return True, session_data.get('user', {})
    
    return False, None


def is_admin_user(user_info):
    """检查用户是否是管理员"""
    if not user_info:
        return False
    return user_info.get("is_admin", False)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """自定义请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("[%s] %s" % (timestamp, args[0]))
    
    def send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)
        
        # 登录回调处理
        if path == '/auth/callback':
            self.handle_auth_callback(query)
            return
        
        # 退出登录
        if path == '/logout':
            self.handle_logout()
            return
        
        # API路由 - 检查登录状态
        if path.startswith('/api/'):
            # 检查是否已登录（除了特定的公开接口）
            if path not in ['/api/ip']:
                is_logged, user_info = is_logged_in(self.headers)
                if not is_logged:
                    self.send_error_response(401, '未登录，请先登录')
                    return
                # 保存用户信息供后续使用
                self.current_user = user_info
            
            if path == '/api/records':
                self.handle_get_records()
                return
            
            if path == '/api/mode':
                self.handle_get_mode()
                return
            
            if path == '/api/config':
                self.handle_get_config()
                return
            
            if path == '/api/period':
                self.handle_get_period()
                return
            
            if path == '/api/ip':
                self.handle_get_ip()
                return
            
            if path == '/api/user/info':
                self.handle_get_user_info()
                return
            
            # 数据导出接口（供同步服务器调用，不需要登录）
            if path == '/api/export/data':
                self.handle_export_data()
                return
            
            # 处理根路径 / 和 /index.html
        if path in ['/', '/index.html']:
            is_logged, user_info = is_logged_in(self.headers)
            if not is_logged:
                # 未登录，重定向到登录页面
                self.redirect_to_login()
                return
            # 已登录，保存用户信息并返回 index.html
            self.current_user = user_info
            path = '/index.html'
            self.serve_file(path)
            return
        
        # 提供登录页面
        if path == '/login.html':
            self.serve_login_page()
            return
        
        # 检查是否是受保护的文件
        protected_files = ['/script.js', '/styles.css', '/data.json']
        if path in protected_files:
            is_logged, user_info = is_logged_in(self.headers)
            if not is_logged:
                # 未登录，重定向到登录页面
                self.redirect_to_login()
                return
            self.current_user = user_info
        
        # 其他静态文件
        self.serve_file(path)
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API路由 - 检查登录状态
        if path.startswith('/api/'):
            is_logged, user_info = is_logged_in(self.headers)
            if not is_logged:
                self.send_error_response(401, '未登录，请先登录')
                return
            self.current_user = user_info
        
        if path == '/api/records':
            self.handle_post_record()
            return
        
            if path == '/api/mode':
                self.handle_post_mode()
                return
            
            if path == '/api/config':
                self.handle_post_config()
                return
            
            self.send_error(404, "Not found")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 检查登录状态
        is_logged, user_info = is_logged_in(self.headers)
        if not is_logged:
            self.send_error_response(401, '未登录，请先登录')
            return
        self.current_user = user_info
        
        if path == '/api/records':
            self.handle_delete_record()
            return
        
        self.send_error(404, "Not found")
    
    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            if sys.version_info[0] >= 3:
                return self.rfile.read(content_length).decode('utf-8')
            else:
                return self.rfile.read(content_length)
        return '{}'
    
    def handle_auth_callback(self, query):
        """处理登录回调"""
        token = query.get('token', [''])[0]
        
        if not token:
            self.send_error_response(400, '缺少 token')
            return
        
        # 验证 token
        result = verify_token_with_auth_service(token)
        
        if not result["valid"]:
            self.send_error_response(401, result.get("error", "Token 无效"))
            return
        
        # 创建 session
        import uuid
        session_id = str(uuid.uuid4())
        now = datetime.datetime.now()
        sessions[session_id] = {
            'user': result["user"],
            'created_at': now,
            'last_activity': now
        }
        
        # 设置 cookie 并重定向到首页
        self.send_response(302)
        self.send_header('Location', '/')
        self.send_header('Set-Cookie', '{}={}; Path=/; HttpOnly'.format(SESSION_COOKIE_NAME, session_id))
        self.end_headers()
    
    def handle_logout(self):
        """处理退出登录"""
        session_token = get_session_from_cookie(self.headers)
        if session_token and session_token in sessions:
            del sessions[session_token]
        
        # 清除 cookie 并重定向
        self.send_response(302)
        self.send_header('Location', '/login.html')
        self.send_header('Set-Cookie', '{}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT'.format(SESSION_COOKIE_NAME))
        self.end_headers()
    
    def redirect_to_login(self):
        """重定向到登录页面"""
        self.send_response(302)
        self.send_header('Location', '/login.html')
        self.end_headers()
    
    def serve_login_page(self):
        """提供登录页面"""
        # 使用服务器实际IP构建回调URL，支持其他电脑访问
        callback_url = "http://%s:%d/auth/callback" % (SERVER_IP, PORT)
        login_url = "%s/login?redirect=%s" % (AUTH_SERVICE_URL, callback_url)
        
        # 使用字符串拼接避免与CSS中的百分号冲突
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '    <title>签到系统 - 登录</title>',
            '    <style>',
            '        * { margin: 0; padding: 0; box-sizing: border-box; }',
            '        body {',
            '            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;',
            '            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            '            min-height: 100vh;',
            '            display: flex;',
            '            justify-content: center;',
            '            align-items: center;',
            '        }',
            '        .login-container {',
            '            background: white;',
            '            padding: 40px;',
            '            border-radius: 12px;',
            '            box-shadow: 0 20px 60px rgba(0,0,0,0.3);',
            '            width: 100%;',
            '            max-width: 400px;',
            '            text-align: center;',
            '        }',
            '        .logo {',
            '            width: 80px;',
            '            height: 80px;',
            '            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            '            border-radius: 50%;',
            '            margin: 0 auto 20px;',
            '            display: flex;',
            '            align-items: center;',
            '            justify-content: center;',
            '            color: white;',
            '            font-size: 32px;',
            '        }',
            '        h1 { color: #333; margin-bottom: 10px; font-size: 24px; }',
            '        .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }',
            '        .login-btn {',
            '            display: inline-block;',
            '            width: 100%;',
            '            padding: 14px 24px;',
            '            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',
            '            color: white;',
            '            text-decoration: none;',
            '            border-radius: 8px;',
            '            font-size: 16px;',
            '            font-weight: 500;',
            '            transition: transform 0.2s, box-shadow 0.2s;',
            '            border: none;',
            '            cursor: pointer;',
            '        }',
            '        .login-btn:hover {',
            '            transform: translateY(-2px);',
            '            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);',
            '        }',
            '        .features {',
            '            margin-top: 30px;',
            '            padding-top: 30px;',
            '            border-top: 1px solid #eee;',
            '            text-align: left;',
            '        }',
            '        .feature-item {',
            '            display: flex;',
            '            align-items: center;',
            '            margin-bottom: 12px;',
            '            color: #666;',
            '            font-size: 14px;',
            '        }',
            '        .feature-item::before {',
            '            content: "✓";',
            '            display: inline-flex;',
            '            align-items: center;',
            '            justify-content: center;',
            '            width: 20px;',
            '            height: 20px;',
            '            background: #10b981;',
            '            color: white;',
            '            border-radius: 50%;',
            '            margin-right: 10px;',
            '            font-size: 12px;',
            '        }',
            '    </style>',
            '</head>',
            '<body>',
            '    <div class="login-container">',
            '        <div class="logo">📋</div>',
            '        <h1>签到系统</h1>',
            '        <p class="subtitle">请使用企业 OA 账号登录</p>',
            '        <a href="' + login_url + '" class="login-btn">企业账号登录</a>',
            '        <div class="features">',
            '            <div class="feature-item">使用现有 OA 账号，无需额外注册</div>',
            '            <div class="feature-item">安全加密传输，保护账号信息</div>',
            '            <div class="feature-item">自动同步部门信息</div>',
            '        </div>',
            '    </div>',
            '</body>',
            '</html>'
        ]
        
        html_content = '\n'.join(html_parts)
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        
        if sys.version_info[0] >= 3:
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.wfile.write(html_content)
    
    def serve_file(self, path):
        """提供静态文件服务"""
        # 移除开头的 /
        file_path = os.path.join(os.path.dirname(__file__), path.lstrip('/'))
        
        # 安全检查：防止目录遍历
        base_dir = os.path.abspath(os.path.dirname(__file__))
        target_path = os.path.abspath(file_path)
        if not target_path.startswith(base_dir):
            self.send_error(403, "Forbidden")
            return
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            # 为HTML和JS文件添加禁用缓存头部
            if ext in ['.html', '.js']:
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
            self.send_cors_headers()
            self.end_headers()
            
            # 二进制模式读取
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")
    
    def handle_get_records(self):
        """获取签到记录（权限控制：管理员-全部历史，普通员工-当天，外委-无权限）"""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        # 检查用户登录状态
        if not hasattr(self, 'current_user') or not self.current_user:
            self.send_error_response(401, '未登录，请先登录')
            return
        
        user = self.current_user
        
        # 1. 外委成员：无查看权限
        if user.get('is_external', False):
            self.send_error_response(403, '外委成员无查看记录权限')
            return
        
        # 2. 普通员工（OA账号）：只能查看当天数据
        if not user.get('is_admin', False):
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            get_or_create_daily_records(today_str)
            data = read_data()
            # 只返回当天的数据
            today_data = {today_str: data.get(today_str, [])} if today_str in data else {}
            self.send_json_response(today_data)
            return
        
        # 3. 管理员：可以查看所有历史数据
        # 如果指定了日期，确保该日期的记录存在
        date_param = query_params.get('date', [None])[0]
        if date_param:
            get_or_create_daily_records(date_param)
        else:
            # 自动创建当天的空记录（确保每天都有数据）
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            get_or_create_daily_records(today_str)
        
        data = read_data()
        self.send_json_response(data)
    
    def handle_get_mode(self):
        """获取模式设置"""
        mode = read_mode()
        self.send_json_response(mode)
    
    def handle_get_config(self):
        """获取系统配置（包括签到时间设置）"""
        config = read_config()
        self.send_json_response(config)
    
    def handle_get_period(self):
        """获取当前签到时段信息"""
        period_info = get_current_period()
        # 添加完整的时间配置信息
        response = {
            'current': period_info,
            'schedule': SIGNIN_SCHEDULE
        }
        self.send_json_response(response)
    
    def handle_post_config(self):
        """保存系统配置（管理员权限）- 只能开启/关闭时间限制，不能修改时间"""
        try:
            # 检查是否是管理员
            if not hasattr(self, 'current_user') or not is_admin_user(self.current_user):
                self.send_error_response(403, '权限不足，只有管理员可以修改配置')
                return
            
            body = self.read_body()
            new_config = json.loads(body)
            
            # 读取现有配置
            config = read_config()
            
            # 管理员只能修改是否启用时间限制，不能修改签到时间
            # 签到时间固定为代码中的 SIGNIN_START_TIME（默认 17:30）
            if 'enable_time_limit' in new_config:
                config['enable_time_limit'] = bool(new_config['enable_time_limit'])
            
            # 强制保持固定时间（防止通过 API 绕过限制）
            config['signin_start_time'] = SIGNIN_START_TIME
            
            # 保存配置
            if save_config(config):
                self.send_json_response({'success': True, 'config': config})
            else:
                self.send_error_response(500, '保存配置失败')
        
        except ValueError:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_export_data(self):
        """导出所有签到数据（供同步服务器调用）"""
        # 允许内网IP访问，不需要登录
        client_ip = self.client_address[0]
        
        # 检查是否是内网IP（可选的安全检查）
        is_private = (
            client_ip.startswith('10.') or
            client_ip.startswith('172.16.') or
            client_ip.startswith('172.17.') or
            client_ip.startswith('172.18.') or
            client_ip.startswith('172.19.') or
            client_ip.startswith('172.2') or
            client_ip.startswith('172.30.') or
            client_ip.startswith('172.31.') or
            client_ip.startswith('192.168.') or
            client_ip == '127.0.0.1'
        )
        
        if not is_private:
            self.send_error_response(403, '只允许内网访问')
            return
        
        data = read_data()
        
        # 添加元信息
        export_data = {
            'export_time': datetime.datetime.now().isoformat(),
            'server_ip': client_ip,
            'record_count': len(data),
            'data': data
        }
        
        self.send_json_response(export_data)
    
    def handle_get_ip(self):
        """获取客户端IP"""
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
        self.send_json_response({'ip': client_ip})
    
    def handle_get_user_info(self):
        """获取当前用户信息"""
        if hasattr(self, 'current_user'):
            self.send_json_response(self.current_user)
        else:
            self.send_error_response(401, '未登录')
    
    def handle_post_record(self):
        """添加或更新签到记录"""
        try:
            body = self.read_body()
            data = json.loads(body)
            
            date = data.get('date')
            record = data.get('record')
            
            if not date or not record:
                self.send_error_response(400, 'Missing parameters')
                return
            
            # 获取客户端IP
            client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
            record['ip'] = client_ip  # 记录IP地址
            
            # 确保该日期的记录已初始化（如果当天还没有记录，创建空记录）
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            if date == today_str:
                # 当天签到，确保当天记录存在
                records = get_or_create_daily_records(date)
            else:
                # 补签其他日期，也确保记录存在
                records = get_or_create_daily_records(date)
            
            # 检查是否为管理员操作（补签/修改）
            is_admin_action = record.get('isAdminAction') == True
            department = record.get('department')
            
            # 如果是补签/修改操作，检查是否是管理员
            if is_admin_action:
                if not hasattr(self, 'current_user') or not is_admin_user(self.current_user):
                    self.send_error_response(403, '权限不足，只有管理员可以执行补签/修改操作')
                    return
            
            # 只有普通签到才进行时间限制检查（管理员补签不受限制）
            period_info = None
            if not is_admin_action:
                can_signin, time_msg = check_signin_time()
                if not can_signin:
                    self.send_error_response(403, time_msg)
                    return
                # 获取当前时段信息（用于标记迟到）
                period_info = get_current_period()
            
            # 只有普通签到才进行IP限制检查（如果启用了该功能）
            if ENABLE_IP_RESTRICTION and not is_admin_action:
                # 检查该IP今天是否已经签过到（同一部门可以重复签到换人，不同部门不行）
                for r in records:
                    if r.get('ip') == client_ip and r.get('department') != department:
                        self.send_error_response(403, '签到失败，当前IP已签到，请更换IP签到')
                        return
            
            # 查找并更新对应部门的记录
            found = False
            for r in records:
                if r.get('department') == department:
                    # 更新记录（保留displayName）
                    display_name = r.get('displayName')
                    r.update(record)
                    r['displayName'] = display_name
                    r['isDefault'] = False
                    # 添加时段信息和迟到标记
                    if period_info:
                        r['period'] = period_info['period']  # morning/evening
                        r['period_name'] = period_info['period_name']  # 早上签到/晚上签到
                        r['is_late'] = period_info['is_late']  # 是否迟到
                    found = True
                    break
            
            if not found:
                # 如果找不到对应部门（不应该发生），添加新记录
                if period_info:
                    record['period'] = period_info['period']
                    record['period_name'] = period_info['period_name']
                    record['is_late'] = period_info['is_late']
                records.append(record)
            
            # 读取完整数据，更新当前日期，保留其他日期
            all_data = read_data()
            all_data[date] = records
            save_data(all_data)
            
            # 签到成功后，自动同步到云文档（后台异步执行，不阻塞响应）
            if ENABLE_AUTO_SYNC:
                import threading
                sync_thread = threading.Thread(target=sync_to_kdocs)
                sync_thread.daemon = True
                sync_thread.start()
            
            self.send_json_response({'success': True})
            
        except ValueError as e:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_delete_record(self):
        """删除签到记录"""
        try:
            body = self.read_body()
            data = json.loads(body)
            
            date = data.get('date')
            department = data.get('department')
            name = data.get('name')
            
            if not date or not department or not name:
                self.send_error_response(400, 'Missing parameters')
                return
            
            records = read_data()
            
            if date in records:
                records[date] = [
                    r for r in records[date] 
                    if not (r.get('department') == department and r.get('name') == name)
                ]
                
                # 如果该日期没有记录了，删除该日期
                if len(records[date]) == 0:
                    del records[date]
                
                save_data(records)
            
            self.send_json_response({'success': True})
            
        except ValueError:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_post_mode(self):
        """保存模式设置"""
        try:
            body = self.read_body()
            mode = json.loads(body)
            
            # 保存模式
            with open(MODE_FILE, 'w') as f:
                json.dump(mode, f, ensure_ascii=False, indent=2)
            
            self.send_json_response({'success': True})
            
        except ValueError:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        if sys.version_info[0] >= 3:
            self.wfile.write(response.encode('utf-8'))
        else:
            self.wfile.write(response)
    
    def send_error_response(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps({'error': message}, ensure_ascii=False)
        if sys.version_info[0] >= 3:
            self.wfile.write(response.encode('utf-8'))
        else:
            self.wfile.write(response)


def main():
    """主函数"""
    init_data_files()
    
    server = socketserver.TCPServer(("", PORT), RequestHandler)
    
    print("=" * 50)
    print("  南宁公司值班签到系统 - 带登录保护")
    print("=" * 50)
    print("")
    print("服务器启动成功！")
    print("")
    print("访问地址：")
    print("  - 本机访问：http://localhost:%d" % PORT)
    print("  - 局域网访问：http://%s:%d" % (SERVER_IP, PORT))
    print("")
    print("登录流程：")
    print("  1. 访问 http://%s:%d" % (SERVER_IP, PORT))
    print("  2. 点击【企业账号登录】")
    print("  3. 输入 OA 账号密码")
    print("  4. 登录成功后进入签到页面")
    print("")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        server.shutdown()


if __name__ == '__main__':
    main()
