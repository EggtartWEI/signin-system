# 白名单功能部署说明

## 配置
1. 在 `.env` 中设置以下字段：
   - `WHITELIST_ENABLED=true`
   - `WHITELIST_DB_PATH=data/whitelist.db`
   - `ADMIN_API_TOKEN=change_me`（请替换为强随机值）
   - `ADMIN_CONTACT_NAME` / `ADMIN_CONTACT_PHONE` / `ADMIN_CONTACT_EMAIL`

2. 如需自定义默认白名单，可设置：
   - `WHITELIST_DEFAULT_IDS`（逗号分隔）
   - `WHITELIST_DEFAULT_NAMES`（逗号分隔）

## 初始化
执行初始化脚本（可重复执行，自动去重）：
```bash
python scripts/init_whitelist.py
```

## 管理接口
使用管理员 Token 调用接口：
```bash
curl -H "Authorization: Bearer <ADMIN_API_TOKEN>" ^
  -H "Content-Type: application/json" ^
  -X POST ^
  -d "{\"user_id\":\"12061413\",\"user_name\":\"示例用户\",\"enabled\":true}" ^
  http://localhost:8001/api/admin/whitelist/users
```

```bash
curl -H "Authorization: Bearer <ADMIN_API_TOKEN>" ^
  http://localhost:8001/api/admin/whitelist/users
```

```bash
curl http://localhost:8001/api/admin/contact
```

## 说明
- 白名单开启后，非白名单用户登录将返回 403，并携带管理员联系方式。
- 初始化脚本默认写入「李茗」「韦学远」。
