# 值班签到系统 v1.0

## 项目简介

值班签到系统用于记录公司各部门值班人员的签到情况，支持 OA 账号和外委账号登录，具备实时数据同步、权限管理和数据导出等功能。

## 主要功能

### 1. 用户登录
- **OA 账号登录**：公司员工使用 OA 账号密码登录
- **外委账号登录**：外包人员使用专用账号登录
- **管理员账号**：本地管理员账号（admin）

### 2. 签到功能
- 支持 GPS 定位签到
- 部门分类选择（公司值班、计划部、运行部、D标、生产管理、A标、其他）
- 签到时间记录
- 签到状态显示（已签到/未签到/迟到）

### 3. 权限管理
- 普通用户：仅可签到
- 管理员：可查看所有记录、补签、修改、导出数据
- IP 限制：同一 IP 一天只能签到一个部门（可配置）

### 4. 数据同步
- **实时同步**：签到后自动同步当天数据到金山云文档
- **定时同步**：每天晚上 20:00 自动同步所有历史数据
- 支持双表格同步：历史签到数据 + 当天签到数据

### 5. 密码管理（外委账号）
- **修改密码**：需要原密码
- **重置密码**：通过邮箱接收随机生成的 8 位密码

### 6. 会话管理
- 30 分钟无操作自动退出
- 手动退出登录功能
- Session 超时清理

## 技术架构

### 后端服务
| 服务 | 技术 | 端口 | 说明 |
|-----|------|------|------|
| 认证服务 | FastAPI (Python) | 8001 | 处理登录认证 |
| 签到系统 | HTTP Server (Python) | 3000 | 处理签到业务 |
| 定时同步 | Python 脚本 | - | 云文档数据同步 |

### 数据存储
- `data.json`：签到记录数据
- `external_users.json`：外委账号信息
- `mode.json`：系统模式配置
- 内存 Session：用户登录状态

### 外部集成
- **金山云文档**：通过 AirScript Webhook 同步数据
- **邮件服务**：QQ 邮箱 SMTP 发送重置密码邮件

## 文件结构

```
工程建设/
├── login/                          # 认证服务
│   ├── attendance_login_only.py   # 认证服务主程序
│   ├── external_users.json        # 外委账号数据
│   ├── login_page.html            # 登录页面
│   └── ...
├── kdocs_sync/                     # 云文档同步
│   ├── sync_module.py             # 同步模块
│   ├── sync_via_webhook.py        # Webhook 同步脚本
│   ├── sync_scheduler.py          # 定时调度器
│   └── ...
├── server_with_auth.py            # 签到系统主程序
├── index.html                     # 签到页面
├── script.js                      # 前端脚本
├── styles.css                     # 样式文件
└── data.json                      # 签到数据
```

## 配置说明

### 环境变量（login/.env）
```bash
# 管理员配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# 白名单配置
WHITELIST_ENABLED=false

# 日志配置
LOG_DIR=logs
LOG_LEVEL=INFO
```

### 邮件配置（login/attendance_login_only.py）
```python
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "2377083243@qq.com"
SMTP_PASSWORD = "your_auth_code"
```

### 云文档配置（kdocs_sync/sync_module.py）
```python
AIRSCRIPT_WEBHOOK_URL = "https://www.kdocs.cn/api/v3/ide/file/..."
AIRSCRIPT_TOKEN = "your_token"
```

## 启动方式

### 开发环境
```bash
# 1. 启动认证服务
cd login
python attendance_login_only.py

# 2. 启动签到系统（新终端）
cd ..
python server_with_auth.py

# 3. 启动定时同步（可选，新终端）
cd kdocs_sync
python sync_scheduler.py
```

### 访问地址
- 签到系统：http://localhost:3000
- 认证服务：http://localhost:8001

## 定时任务

### Windows 任务计划程序
```powershell
# 创建定时任务（每天晚上 20:00）
cd kdocs_sync
.\创建定时任务.ps1
```

### 手动执行同步
```bash
cd kdocs_sync
python sync_via_webhook.py
```

## 版本历史

### v1.0 (当前版本)
- ✅ OA 账号登录
- ✅ 外委账号登录
- ✅ GPS 定位签到
- ✅ 部门分类管理
- ✅ 管理员功能（补签、修改、导出）
- ✅ 云文档实时同步
- ✅ 云文档定时同步
- ✅ 外委账号密码修改/重置
- ✅ 会话超时管理
- ✅ IP 限制功能
- ✅ 并发安全保护

## 安全特性

1. **密码加密**：OA 账号使用 RSA 加密传输
2. **Session 管理**：30 分钟超时，自动清理
3. **并发保护**：原子写操作，防止数据覆盖
4. **访问控制**：IP 白名单、部门签到限制
5. **数据备份**：自动创建当天空记录，防止数据丢失

## 注意事项

1. **重启后需重新登录**：Session 存储在内存中
2. **定时任务需单独配置**：Windows 任务计划程序或 Linux cron
3. **云文档配置需手动设置**：Webhook URL 和 Token
4. **邮件服务需配置正确的授权码**：不是邮箱密码

## 后续优化方向

- [ ] Docker 容器化部署
- [ ] Redis 存储 Session
- [ ] 数据库替代 JSON 文件
- [ ] 签到数据统计报表
- [ ] 移动端 APP

## 维护人员

- 开发：[你的名字]
- 部署：系统管理员
- 联系：管理员联系方式

---

**最后更新**：2025年
