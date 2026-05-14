/**
 * 签到数据同步 - AirScript Webhook 脚本
 * 入口函数: sync_task (根据 Webhook URL)
 */

function sync_task(data) {
    try {
        console.log("=== 开始同步 ===");
        console.log("收到数据行数: " + (data.data ? data.data.length : 0));
        
        // 获取当前活动表格
        var sheet = Application.ActiveSheet;
        
        if (!sheet) {
            console.log("错误: 无法获取表格");
            return { code: -1, msg: "无法获取表格" };
        }
        
        console.log("获取表格成功");
        
        // 获取数据
        var rows = data.data;
        if (!rows || rows.length === 0) {
            console.log("错误: 没有数据");
            return { code: -1, msg: "没有数据" };
        }
        
        // 写入数据
        var count = 0;
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            for (var j = 0; j < row.length; j++) {
                sheet.Cells(i + 1, j + 1).Value2 = row[j];
            }
            count++;
        }
        
        console.log("写入完成: " + count + " 行");
        console.log("=== 同步成功 ===");
        
        return {
            code: 0,
            success: true,
            msg: "同步成功",
            rows: count
        };
        
    } catch (e) {
        console.log("错误: " + e.message);
        return {
            code: -1,
            success: false,
            msg: "错误: " + e.message
        };
    }
}

// 测试函数
function test() {
    var testData = {
        data: [
            ["日期", "部门", "姓名", "电话", "记录时间"],
            ["2025-01-12", "技术部", "张三", "13800138000", "09:00"],
            ["2025-01-12", "销售部", "李四", "13900139000", "09:30"]
        ],
        sync_time: "2025-01-12 10:00:00",
        total_rows: 2
    };
    
    var result = sync_task(testData);
    console.log("测试结果: " + JSON.stringify(result));
}
