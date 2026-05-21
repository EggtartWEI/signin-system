#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
签到数据同步到金山云文档 - 通过 AirScript Webhook (官方标准版)
用法: python sync_via_webhook.py

官方文档：https://airsheet.wps.cn/docs/apitoken/api.html

此脚本通过调用金山文档 AirScript 的 Webhook 来同步数据
需要在云文档中创建 AirScript 脚本并发布 Webhook

调用方式：
POST /api/v3/ide/file/:file_id/script/:script_id/sync_task
Header: AirScript-Token: <脚本令牌>
Body: {
  "Context": {
    "argv": {
      "data": [...],
      "sync_time": "...",
      "total_rows": ...
    }
  }
}

注意：此脚本现在使用 sync_module.py 作为底层实现，保持向后兼容
"""

import sys
import os

# 导入新的同步模块
from sync_module import sync_via_webhook, AIRSCRIPT_WEBHOOK_URL, AIRSCRIPT_TOKEN


def main():
    """主函数"""
    # 检查是否配置了 Webhook URL 和脚本令牌
    if not AIRSCRIPT_WEBHOOK_URL or not AIRSCRIPT_TOKEN:
        print("=" * 70)
        print("签到数据同步到金山云文档 (AirScript Webhook)")
        print("=" * 70)
        print()
        print("错误: 未配置 AirScript Webhook URL 或脚本令牌")
        print()
        print("请按以下步骤操作:")
        print("1. 在金山文档中打开目标表格")
        print("2. 点击【工具】-【脚本】-【新建脚本】")
        print("3. 复制 airscript_final.js 的内容到编辑器")
        print("4. 保存脚本（Ctrl+S）")
        print("5. 点击【发布】→【Webhook】获取 Webhook URL")
        print("6. 点击【发布】→【脚本令牌】生成令牌")
        print("7. 将 Webhook URL 和脚本令牌填入 sync_module.py")
        print()
        print("官方文档: https://airsheet.wps.cn/docs/apitoken/api.html")
        print()
        sys.exit(1)
    
    try:
        if sync_via_webhook(AIRSCRIPT_WEBHOOK_URL):
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
