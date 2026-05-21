# 签到数据云同步 - 删除 Windows 定时任务

Write-Host "============================================" -ForegroundColor Yellow
Write-Host "  删除签到数据云同步定时任务" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""

$taskName = "签到数据云同步"

# 检查任务是否存在
try {
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $existingTask) {
        Write-Host "任务 '$taskName' 不存在" -ForegroundColor Gray
        exit 0
    }
    
    Write-Host "找到任务: $taskName" -ForegroundColor Cyan
    Write-Host ""
    
    # 确认删除
    $response = Read-Host "确认删除此定时任务? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Green
        Write-Host "  任务已删除！" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "已取消删除" -ForegroundColor Gray
    }
    
} catch {
    Write-Host ""
    Write-Host "删除任务时出错: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
