#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
签到数据同步定时任务
每天晚上 20:00 自动执行同步

用法:
1. 直接运行: python sync_scheduler.py
2. 作为后台服务运行: python sync_scheduler.py --daemon
3. 立即执行一次: python sync_scheduler.py --now
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta

# 导入同步函数
from sync_module import sync_all_data, AIRSCRIPT_WEBHOOK_URL


def run_sync():
    """执行同步任务"""
    print("\n" + "=" * 70)
    print(f"定时任务触发 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        success, message = sync_all_data()
        if success:
            print(f"\n✓ 同步成功 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  {message}")
        else:
            print(f"\n✗ 同步失败 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  {message}")
        return success
    except Exception as e:
        print(f"\n✗ 同步异常: {str(e)}")
        return False


def wait_until(target_time):
    """等待直到目标时间"""
    now = datetime.now()
    target = now.replace(hour=target_time.hour, minute=target_time.minute, second=target_time.second, microsecond=0)
    
    # 如果目标时间已过，等到明天
    if target <= now:
        target += timedelta(days=1)
    
    wait_seconds = (target - now).total_seconds()
    
    print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"下次同步时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"等待: {int(wait_seconds)} 秒 ({int(wait_seconds / 60)} 分钟)")
    
    time.sleep(wait_seconds)


def run_scheduler():
    """运行定时调度器"""
    # 设置每天 20:00 执行
    sync_time = datetime.strptime("20:00:00", "%H:%M:%S").time()
    
    print("=" * 70)
    print("签到数据同步定时任务")
    print("=" * 70)
    print(f"\n定时设置: 每天 {sync_time.strftime('%H:%M')} 自动同步")
    print("按 Ctrl+C 停止定时任务")
    print("=" * 70)
    
    try:
        while True:
            # 等待到同步时间
            wait_until(sync_time)
            
            # 执行同步
            run_sync()
            
            # 等待 1 分钟，避免重复执行
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n定时任务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n定时任务异常: {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='签到数据同步定时任务')
    parser.add_argument('--daemon', action='store_true', help='作为后台服务运行')
    parser.add_argument('--now', action='store_true', help='立即执行一次同步')
    parser.add_argument('--time', type=str, default='20:00', help='设置同步时间 (默认: 20:00)')
    
    args = parser.parse_args()
    
    if args.now:
        # 立即执行一次
        print("立即执行同步...")
        success = run_sync()
        sys.exit(0 if success else 1)
    else:
        # 运行定时调度器
        run_scheduler()


if __name__ == '__main__':
    main()
