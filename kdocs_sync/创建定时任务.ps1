# 签到数据云同步 - 创建 Windows 定时任务
# 每天晚上 20:00 自动执行

Write-Host "============================================" -ForegroundColor Green
Write-Host "  创建签到数据云同步定时任务" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# 获取当前目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$batchFile = Join-Path $scriptPath "定时同步任务.bat"

# 检查批处理文件是否存在
if (-not (Test-Path $batchFile)) {
    Write-Host "错误: 找不到定时同步任务.bat" -ForegroundColor Red
    exit 1
}

Write-Host "批处理文件路径: $batchFile" -ForegroundColor Cyan
Write-Host ""

# 任务名称
$taskName = "签到数据云同步"

# 检查任务是否已存在
try {
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "任务 '$taskName' 已存在，是否重新创建?" -ForegroundColor Yellow
        $response = Read-Host "输入 Y 重新创建，N 取消 (Y/N)"
        if ($response -ne 'Y' -and $response -ne 'y') {
            Write-Host "已取消" -ForegroundColor Gray
            exit 0
        }
        # 删除现有任务
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "已删除现有任务" -ForegroundColor Green
    }
} catch {
    # 任务不存在，继续创建
}

Write-Host ""
Write-Host "正在创建定时任务..." -ForegroundColor Cyan

# 创建任务操作
$action = New-ScheduledTaskAction -Execute $batchFile -WorkingDirectory $scriptPath

# 创建任务触发器（每天 20:00）
$trigger = New-ScheduledTaskTrigger -Daily -At "20:00"

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

# 创建任务对象
$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "每天晚上8点自动同步签到数据到金山云文档"

# 注册任务（使用当前用户）
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -InputObject $task `
        -User $env:USERNAME `
        -RunLevel Highest `
        -Force
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  定时任务创建成功！" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "任务详情:" -ForegroundColor Cyan
    Write-Host "  名称: $taskName" -ForegroundColor White
    Write-Host "  执行时间: 每天 20:00" -ForegroundColor White
    Write-Host "  执行文件: $batchFile" -ForegroundColor White
    Write-Host ""
    Write-Host "操作选项:" -ForegroundColor Yellow
    Write-Host "  1. 立即运行任务: 在任务计划程序中右键点击任务 -> 运行" -ForegroundColor White
    Write-Host "  2. 修改设置: 在任务计划程序中右键点击任务 -> 属性" -ForegroundColor White
    Write-Host "  3. 禁用任务: 在任务计划程序中右键点击任务 -> 禁用" -ForegroundColor White
    Write-Host ""
    Write-Host "打开任务计划程序?" -ForegroundColor Yellow
    $openScheduler = Read-Host "输入 Y 打开，N 退出 (Y/N)"
    if ($openScheduler -eq 'Y' -or $openScheduler -eq 'y') {
        Start-Process taskchd.msc
    }
    
} catch {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "  创建任务失败！" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "请尝试手动创建:" -ForegroundColor Yellow
    Write-Host "  1. 打开任务计划程序 (taskschd.msc)" -ForegroundColor White
    Write-Host "  2. 创建基本任务，设置每天 20:00 运行" -ForegroundColor White
    Write-Host "  3. 操作选择: $batchFile" -ForegroundColor White
    exit 1
}
