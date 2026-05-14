# 签到数据同步到金山云文档

此文件夹包含将本地签到数据同步到金山云文档的所有相关文件。

## 文件说明

### Python 脚本
- **sync_via_webhook.py** - 主同步脚本，通过 Webhook 方式同步数据

### AirScript 脚本（用于金山文档）
- **airscript_final.js** - 最终版 AirScript 脚本（推荐）
- **airscript_sync_task.js** - sync_task 版本
- **airscript_webhook.js** - webhook 版本

### 批处理文件
- **同步到云文档.bat** - Windows 批处理文件，双击即可运行同步

### 数据文件
- **data.json** - 签到数据文件（源数据）

## 使用方法

### 方法一：命令行运行
```bash
python sync_via_webhook.py
```

### 方法二：双击批处理文件
双击运行 `同步到云文档.bat`

## 配置步骤

### 1. 在金山文档中创建 AirScript 脚本
1. 打开文档：https://www.kdocs.cn/l/cqrKey08JOk2
2. 点击【工具】→【脚本】→【新建脚本】
3. 复制 `airscript_final.js` 的内容到编辑器
4. 按 Ctrl+S 保存

### 2. 发布 Webhook
1. 点击【发布】→【Webhook】
2. 确认入口函数是 `sync_task`
3. 点击【生成 Webhook URL】
4. 复制 URL

### 3. 获取脚本令牌
1. 点击【发布】→【脚本令牌】
2. 生成新的令牌
3. 复制令牌

### 4. 配置 Python 脚本
编辑 `sync_via_webhook.py`，填写：
```python
AIRSCRIPT_WEBHOOK_URL = "https://www.kdocs.cn/api/v3/ide/file/xxx/script/xxx/sync_task"
AIRSCRIPT_TOKEN = "你的脚本令牌"
```

### 5. 测试同步
运行脚本，检查云文档是否更新。

## 注意事项

- AirScript 使用 JavaScript 语言，不是 Python
- 确保 Webhook URL 和脚本令牌正确配置
- 如果同步失败，检查网络连接和文档权限

## 云文档链接
https://www.kdocs.cn/l/cqrKey08JOk2
