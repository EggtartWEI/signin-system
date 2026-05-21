// 后端API地址（部署时根据实际情况修改）
const API_BASE = window.location.origin;
const ADMIN_PASSWORD = 'admin123'; // 管理员密码

// 签到模式配置
let signInMode = 'open'; // 'open' = 内网开放, 'restricted' = 限制IP
let allowedIPs = []; // 允许的IP列表
let currentUserIP = ''; // 当前用户IP
let allRecords = {}; // 缓存所有签到记录

// 部门结构定义（两级：大类 -> 细项）
const deptStructure = {
    '公司值班': ['公司领导', '公司中层', '公司干部'],
    '计划部': ['库管'],
    '运行部': ['管理'],
    'D标': ['北京腾疆'],
    '生产管理': ['管理', '汽机', '锅炉', '输煤环保', '电气专业', '热控专业'],
    'A标': ['管理', '汽机', '锅炉', '电气', '热控', '输煤', '硫硝'],
    '其他': [] // 维护、保安、保洁直接填写
};

// 固定表格布局定义（每个大类及其细项）
// 支持配置每个细项的签到人数（slots），默认为1
const fixedTableLayout = [
    {
        category: '公司值班',
        items: ['公司领导', '公司中层', '公司干部']
    },
    {
        category: '计划部',
        items: ['库管']
    },
    {
        category: '运行部',
        items: ['管理']
    },
    {
        category: 'D标',
        items: ['北京腾疆']
    },
    {
        category: '生产管理',
        items: [
            '管理', 
            '汽机', 
            '锅炉', 
            '输煤环保', 
            {name: '电气专业', slots: 2}, 
            {name: '热控专业', slots: 2}
        ]
    },
    {
        category: 'A标',
        items: ['管理', '汽机', '锅炉', '电气', '热控', '输煤', '硫硝']
    },
    {
        category: '其他',
        items: ['起重维护', '保安', '保洁']
    }
];

// 当前用户信息
let currentUser = null;

// 会话超时设置（30分钟）
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30分钟，单位毫秒
let lastActivityTime = Date.now();
let sessionCheckInterval = null;

// 初始化
async function init() {
    updateTime();
    setInterval(updateTime, 1000);
    
    // 获取当前用户信息
    await loadUserInfo();
    
    // 根据用户权限设置界面
    setupUIBasedOnPermissions();
    
    // 设置用户信息显示和退出按钮
    setupUserControl();
    
    // 启动会话超时检测
    startSessionTimeoutCheck();
    
    await loadModeSettings(); // 加载签到模式设置
    await loadTodayRecords();
    setupEventListeners();
    setDefaultDates();
}

// 设置用户控制区域
function setupUserControl() {
    const userNameSpan = document.getElementById('currentUserName');
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (userNameSpan && currentUser) {
        userNameSpan.textContent = currentUser.name || currentUser.id || '用户';
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// 处理退出登录
async function handleLogout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/logout`, {
            method: 'GET',
            credentials: 'include'
        });
        
        // 清除本地状态
        currentUser = null;
        
        // 停止会话检测
        if (sessionCheckInterval) {
            clearInterval(sessionCheckInterval);
            sessionCheckInterval = null;
        }
        
        // 重定向到登录页面
        window.location.href = '/login.html';
        
    } catch (error) {
        console.error('退出登录出错:', error);
        alert('退出登录失败，请重试');
    }
}

// 更新活动时间
function updateActivityTime() {
    lastActivityTime = Date.now();
}

// 启动会话超时检测
function startSessionTimeoutCheck() {
    // 监听用户活动
    document.addEventListener('click', updateActivityTime);
    document.addEventListener('keypress', updateActivityTime);
    document.addEventListener('mousemove', updateActivityTime);
    document.addEventListener('scroll', updateActivityTime);
    
    // 每分钟检查一次是否超时
    sessionCheckInterval = setInterval(() => {
        const inactiveTime = Date.now() - lastActivityTime;
        
        if (inactiveTime >= SESSION_TIMEOUT) {
            // 会话超时，自动退出
            console.log('会话超时，自动退出登录');
            handleSessionTimeout();
        } else if (inactiveTime >= SESSION_TIMEOUT - 5 * 60 * 1000) {
            // 超时前5分钟提醒
            const remainingMinutes = Math.ceil((SESSION_TIMEOUT - inactiveTime) / 60000);
            console.log(`会话将在 ${remainingMinutes} 分钟后过期`);
        }
    }, 60000); // 每分钟检查一次
}

// 处理会话超时
async function handleSessionTimeout() {
    // 停止检测
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
        sessionCheckInterval = null;
    }
    
    // 显示超时提示
    alert('您已长时间未操作，会话已过期，请重新登录。');
    
    try {
        // 调用后端退出
        await fetch(`${API_BASE}/logout`, {
            method: 'GET',
            credentials: 'include'
        });
    } catch (error) {
        console.error('会话超时退出出错:', error);
    }
    
    // 重定向到登录页面
    window.location.href = '/login.html';
}

// 获取当前用户信息
async function loadUserInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/user/info`);
        if (response.ok) {
            currentUser = await response.json();
            console.log('当前用户:', currentUser);
            // 自动填入用户姓名到签到表单
            autoFillUserName();
        } else {
            console.error('获取用户信息失败');
        }
    } catch (error) {
        console.error('获取用户信息出错:', error);
    }
}

// 自动填入用户姓名到签到表单
function autoFillUserName() {
    // 管理员不自动填写任何信息
    if (currentUser && currentUser.is_admin) {
        console.log('管理员登录，不自动填写信息');
        return;
    }
    
    // 外委账号不自动填写姓名（需要用户自己填写真实姓名）
    if (currentUser && currentUser.is_external) {
        console.log('外委账号登录，不自动填写姓名，需要用户自行填写');
        // 外委账号自动填写部门信息
        autoFillExternalUserDept();
        return;
    }
    
    // 普通OA用户自动填写姓名
    if (currentUser && currentUser.name) {
        const nameInput = document.getElementById('name');
        if (nameInput) {
            nameInput.value = currentUser.name;
            nameInput.readOnly = true;  // 禁用修改
            nameInput.style.backgroundColor = '#f0f0f0';  // 灰色背景表示只读
            console.log('已自动填入姓名:', currentUser.name);
        }
    }
}

// 自动填写外委账号的部门信息
function autoFillExternalUserDept() {
    if (!currentUser || !currentUser.dept_category || !currentUser.dept_subitem) {
        return;
    }
    
    const deptCategory = currentUser.dept_category;
    const deptSubitem = currentUser.dept_subitem;
    
    // 设置部门大类
    const deptCategorySelect = document.getElementById('deptCategory');
    const deptSubItemSelect = document.getElementById('deptSubItem');
    const otherDeptInput = document.getElementById('otherDept');
    
    if (deptCategorySelect) {
        deptCategorySelect.value = deptCategory;
        deptCategorySelect.disabled = true;  // 禁用修改
        deptCategorySelect.style.backgroundColor = '#f0f0f0';
    }
    
    // 直接设置部门细项（不通过事件触发）
    if (deptCategory === '其他') {
        // 其他部门：显示文本输入框并填入细项
        if (deptSubItemSelect) {
            deptSubItemSelect.disabled = true;
            deptSubItemSelect.innerHTML = '<option value="">请直接填写</option>';
        }
        if (otherDeptInput) {
            otherDeptInput.style.display = 'inline-block';
            otherDeptInput.placeholder = '填写：起重维护/保安/保洁';
            otherDeptInput.value = deptSubitem;
            otherDeptInput.readOnly = true;
            otherDeptInput.style.backgroundColor = '#f0f0f0';
        }
    } else {
        // 标准部门：直接填充细项选项并选中
        if (deptSubItemSelect) {
            deptSubItemSelect.disabled = false;
            otherDeptInput.style.display = 'none';
            
            // 直接填充细项选项
            const items = deptStructure[deptCategory] || [];
            let options = '<option value="">请选择细项</option>';
            items.forEach(item => {
                options += `<option value="${item}">${item}</option>`;
            });
            deptSubItemSelect.innerHTML = options;
            
            // 选中对应的细项
            deptSubItemSelect.value = deptSubitem;
            deptSubItemSelect.disabled = true;
            deptSubItemSelect.style.backgroundColor = '#f0f0f0';
        }
    }
    
    console.log('已自动填入部门:', deptCategory, '-', deptSubitem);
}

// 根据用户权限设置界面
function setupUIBasedOnPermissions() {
    const isAdmin = currentUser && currentUser.is_admin;
    
    // 管理员选项按钮
    const adminModeBtn = document.getElementById('adminModeBtn');
    if (adminModeBtn) {
        adminModeBtn.style.display = isAdmin ? 'inline-block' : 'none';
    }
    
    // 管理员操作区域
    const adminSection = document.querySelector('.admin-section');
    if (adminSection) {
        adminSection.style.display = isAdmin ? 'block' : 'none';
    }
    
    // 导出全部数据按钮（仅管理员）
    const exportAllBtn = document.getElementById('exportAllBtn');
    if (exportAllBtn) {
        exportAllBtn.style.display = isAdmin ? 'inline-block' : 'none';
    }
    
    // 清空所有数据按钮（仅管理员）
    const clearAllBtn = document.getElementById('clearAllBtn');
    if (clearAllBtn) {
        clearAllBtn.style.display = isAdmin ? 'inline-block' : 'none';
    }
}

// 更新时间
function updateTime() {
    const now = new Date();
    const dateStr = formatDate(now);
    const weekday = getWeekday(now);
    const timeStr = formatDateTime(now);
    
    document.getElementById('titleDate').textContent = `${dateStr} ${weekday}`;
    document.getElementById('currentTime').textContent = timeStr;
    
    // 更新签到提示
    updateSignInNotice();
}

// 格式化日期 yyyy-mm-dd
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 获取星期几（中文）
function getWeekday(date) {
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return weekdays[date.getDay()];
}

// 判断是否为法定节假日（简化版，主要节假日）
function isHoliday(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    
    // 2026年法定节假日
    const holidays = [
        // 元旦 1月1日-3日
        { month: 1, day: 1 }, { month: 1, day: 2 }, { month: 1, day: 3 },
        // 春节 2月17日-24日（2026年除夕是2月16日，放假8天）
        { month: 2, day: 17 }, { month: 2, day: 18 }, { month: 2, day: 19 },
        { month: 2, day: 20 }, { month: 2, day: 21 }, { month: 2, day: 22 },
        { month: 2, day: 23 }, { month: 2, day: 24 },
        // 清明节 4月4日-6日
        { month: 4, day: 4 }, { month: 4, day: 5 }, { month: 4, day: 6 },
        // 劳动节 5月1日-5日
        { month: 5, day: 1 }, { month: 5, day: 2 }, { month: 5, day: 3 },
        { month: 5, day: 4 }, { month: 5, day: 5 },
        // 端午节 6月19日-21日
        { month: 6, day: 19 }, { month: 6, day: 20 }, { month: 6, day: 21 },
        // 中秋节+国庆节 10月1日-8日
        { month: 10, day: 1 }, { month: 10, day: 2 }, { month: 10, day: 3 },
        { month: 10, day: 4 }, { month: 10, day: 5 }, { month: 10, day: 6 },
        { month: 10, day: 7 }, { month: 10, day: 8 }
    ];
    
    // 检查是否为节假日
    const isHolidayDate = holidays.some(h => h.month === month && h.day === day);
    
    // 周六或周日
    const isWeekend = date.getDay() === 0 || date.getDay() === 6;
    
    return isHolidayDate || isWeekend;
}

// 获取当前时段（上午/下午）
function getCurrentPeriod() {
    const hour = new Date().getHours();
    return hour < 12 ? '上午' : '下午';
}

// 更新签到提示信息
function updateSignInNotice() {
    const now = new Date();
    const isHolidayOrWeekend = isHoliday(now);
    const period = getCurrentPeriod();
    const noticeElement = document.getElementById('timeNotice');
    
    if (!noticeElement) return;
    
    if (isHolidayOrWeekend) {
        // 周末或节假日：上午12:00前，下午17:00前
        if (period === '上午') {
            noticeElement.textContent = '请于当日12:00前完成签到，迟到人员名字将标红，感谢您的配合！';
        } else {
            noticeElement.textContent = '请于当日17:00前完成签到，迟到人员名字将标红，感谢您的配合！';
        }
    } else {
        // 工作日：20:00前
        noticeElement.textContent = '请于当日20:00前完成签到，迟到人员名字将标红，感谢您的配合！';
    }
}

// 格式化日期时间 yyyy-mm-dd hh:mm:ss
function formatDateTime(date) {
    const dateStr = formatDate(date);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${dateStr} ${hours}:${minutes}:${seconds}`;
}

// 格式化时间 hh:mm（用于签到情况显示）
function formatTime(date) {
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

// 设置默认日期
function setDefaultDates() {
    const today = formatDate(new Date());
    document.getElementById('adminDate').value = today;
}

// 从服务器获取所有记录
async function fetchRecords(date = null) {
    try {
        let url = `${API_BASE}/api/records`;
        if (date) {
            url += `?date=${date}`;
        }
        const response = await fetch(url);
        if (!response.ok) throw new Error('获取数据失败');
        allRecords = await response.json();
        return allRecords;
    } catch (error) {
        console.error('获取记录失败:', error);
        alert('无法连接到服务器，请检查网络或联系管理员');
        return {};
    }
}

// 保存记录到服务器
async function saveRecordToServer(date, record) {
    try {
        const response = await fetch(`${API_BASE}/api/records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, record })
        });
        if (!response.ok) {
            if (response.status === 403) {
                const errorData = await response.json();
                alert(errorData.error || '签到失败，当前IP已签到，请更换IP签到');
                return false;
            }
            throw new Error('保存失败');
        }
        return true;
    } catch (error) {
        console.error('保存记录失败:', error);
        if (!error.message.includes('签到失败')) {
            alert('保存失败，请检查网络连接');
        }
        return false;
    }
}

// 从服务器删除记录
async function deleteRecordFromServer(date, department, name) {
    try {
        const response = await fetch(`${API_BASE}/api/records`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, department, name })
        });
        if (!response.ok) throw new Error('删除失败');
        return true;
    } catch (error) {
        console.error('删除记录失败:', error);
        alert('删除失败，请检查网络连接');
        return false;
    }
}

// 获取本地缓存记录（兼容旧代码）
function getRecords() {
    return allRecords;
}

// 检查是否迟到（20:00前签到）
function isLate(signInTime) {
    const date = new Date(signInTime);
    const hours = date.getHours();
    return hours >= 20;
}

// 加载今日签到记录
async function loadTodayRecords() {
    const today = formatDate(new Date());
    await fetchRecords(today); // 从服务器获取最新数据，并确保今日记录已初始化
    const todayRecords = allRecords[today] || [];
    renderSignInTable(todayRecords);
}

// 渲染签到表格（固定布局，每个细项都有固定位置，支持多人签到）
function renderSignInTable(records) {
    const tbody = document.getElementById('signInTableBody');
    tbody.innerHTML = '';
    
    // 创建记录查找映射（department -> record）
    // 现在服务器返回的是固定列表，每个部门只有一条记录
    const recordMap = {};
    records.forEach(record => {
        recordMap[record.department] = record;
    });
    
    // 按固定布局渲染表格
    fixedTableLayout.forEach((group) => {
        // 大类标题行
        const titleRow = document.createElement('tr');
        titleRow.className = 'category-row';
        titleRow.innerHTML = `<td colspan="8">【${group.category}】</td>`;
        tbody.appendChild(titleRow);
        
        // 展开所有细项（包括多签到的行）
        const expandedItems = [];
        group.items.forEach(item => {
            if (typeof item === 'object' && item.slots > 1) {
                // 多签到位置，展开为多个行
                for (let i = 0; i < item.slots; i++) {
                    expandedItems.push({
                        name: item.name,
                        slotIndex: i,
                        deptKey: `${group.category}-${item.name}`,
                        displayName: i === 0 ? item.name : `${item.name}(${i + 1})`
                    });
                }
            } else {
                const itemName = typeof item === 'object' ? item.name : item;
                expandedItems.push({
                    name: itemName,
                    slotIndex: 0,
                    deptKey: group.category === '其他' ? itemName : `${group.category}-${itemName}`,
                    displayName: itemName
                });
            }
        });
        
        // 判断是否为单列布局（公司值班需要单列显示）
        const isSingleColumn = group.category === '公司值班';
        
        // 渲染该大类下的所有细项
        const step = isSingleColumn ? 1 : 2;
        for (let i = 0; i < expandedItems.length; i += step) {
            const row = document.createElement('tr');
            
            // 左列
            const leftItem = expandedItems[i];
            const leftRecord = recordMap[leftItem.deptKey];
            
            if (leftRecord && !leftRecord.isDefault) {
                // 已签到
                const leftNameClass = isLate(leftRecord.signInTime) ? 'late-sign' : '';
                const leftTime = formatTime(new Date(leftRecord.signInTime));
                row.innerHTML = `
                    <td>${leftItem.displayName}</td>
                    <td class="${leftNameClass}">${leftRecord.name}</td>
                    <td>${leftRecord.phone || ''}</td>
                    <td>${leftTime}</td>
                `;
            } else {
                // 未签到，显示空位
                row.innerHTML = `
                    <td>${leftItem.displayName}</td>
                    <td class="unsigned">-</td>
                    <td>-</td>
                    <td>-</td>
                `;
            }
            
            // 右列（仅双列布局时显示）
            if (!isSingleColumn && expandedItems[i + 1]) {
                const rightItem = expandedItems[i + 1];
                const rightRecord = recordMap[rightItem.deptKey];
                
                if (rightRecord && !rightRecord.isDefault) {
                    // 已签到
                    const rightNameClass = isLate(rightRecord.signInTime) ? 'late-sign' : '';
                    const rightTime = formatTime(new Date(rightRecord.signInTime));
                    row.innerHTML += `
                        <td>${rightItem.displayName}</td>
                        <td class="${rightNameClass}">${rightRecord.name}</td>
                        <td>${rightRecord.phone || ''}</td>
                        <td>${rightTime}</td>
                    `;
                } else {
                    // 未签到，显示空位
                    row.innerHTML += `
                        <td>${rightItem.displayName}</td>
                        <td class="unsigned">-</td>
                        <td>-</td>
                        <td>-</td>
                    `;
                }
            } else if (!isSingleColumn) {
                // 双列布局但没有右列，填充空单元格
                row.innerHTML += '<td></td><td></td><td></td><td></td>';
            } else {
                // 单列布局，填充右侧空白（白色背景）
                row.innerHTML += '<td colspan="4"></td>';
            }
            
            tbody.appendChild(row);
        }
    });
}

// 设置事件监听
function setupEventListeners() {
    // 部门大类选择变化
    document.getElementById('deptCategory').addEventListener('change', function() {
        const category = this.value;
        const subItemSelect = document.getElementById('deptSubItem');
        const otherDeptInput = document.getElementById('otherDept');
        
        if (category === '') {
            subItemSelect.disabled = true;
            subItemSelect.innerHTML = '<option value="">请先选择部门大类</option>';
            otherDeptInput.style.display = 'none';
        } else if (category === '其他') {
            subItemSelect.disabled = true;
            subItemSelect.innerHTML = '<option value="">请直接填写</option>';
            otherDeptInput.style.display = 'inline-block';
            otherDeptInput.placeholder = '填写：起重维护/保安/保洁';
        } else {
            subItemSelect.disabled = false;
            otherDeptInput.style.display = 'none';
            
            // 填充细项选项
            const items = deptStructure[category] || [];
            let options = '<option value="">请选择细项</option>';
            items.forEach(item => {
                options += `<option value="${item}">${item}</option>`;
            });
            subItemSelect.innerHTML = options;
        }
    });
    
    // 签到按钮
    document.getElementById('signInBtn').addEventListener('click', handleSignIn);
    
    // 管理员操作按钮
    document.getElementById('submitAdminBtn').addEventListener('click', handleAdminAction);
    
    // 操作类型切换
    document.getElementById('adminAction').addEventListener('change', toggleAdminFields);
    
    // 管理员部门大类选择变化
    document.getElementById('adminDeptCategory').addEventListener('change', function() {
        const category = this.value;
        const subItemSelect = document.getElementById('adminDeptSubItem');
        const otherDeptInput = document.getElementById('adminOtherDept');
        
        if (category === '') {
            subItemSelect.disabled = true;
            subItemSelect.innerHTML = '<option value="">请先选择部门大类</option>';
            otherDeptInput.style.display = 'none';
        } else if (category === '其他') {
            subItemSelect.disabled = true;
            subItemSelect.innerHTML = '<option value="">请直接填写</option>';
            otherDeptInput.style.display = 'inline-block';
            otherDeptInput.placeholder = '填写：起重维护/保安/保洁';
        } else {
            subItemSelect.disabled = false;
            otherDeptInput.style.display = 'none';
            
            // 填充细项选项
            const items = deptStructure[category] || [];
            let options = '<option value="">请选择细项</option>';
            items.forEach(item => {
                options += `<option value="${item}">${item}</option>`;
            });
            subItemSelect.innerHTML = options;
        }
    });
    
    // 清空所有数据按钮
    document.getElementById('clearAllBtn').addEventListener('click', handleClearAll);
    
    // 查询按钮
    document.getElementById('queryBtn').addEventListener('click', handleQuery);
    
    // 导出按钮
    document.getElementById('exportBtn').addEventListener('click', handleExport);
    
    // 导出全部数据按钮
    document.getElementById('exportAllBtn').addEventListener('click', handleExportAll);
    
    // 管理员模式按钮
    document.getElementById('adminModeBtn').addEventListener('click', openModeModal);
    
    // 关闭弹窗按钮
    document.getElementById('closeModeModal').addEventListener('click', closeModeModal);
    document.getElementById('cancelModeBtn').addEventListener('click', closeModeModal);
    
    // 模式选择变化
    document.getElementById('signInMode').addEventListener('change', toggleIPSettings);
    
    
    // 保存模式设置按钮
    document.getElementById('saveModeBtn').addEventListener('click', saveModeSettingsFromModal);
    
    // 点击弹窗外部关闭
    document.getElementById('modeModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModeModal();
        }
    });
}

// 切换管理员表单字段显示
function toggleAdminFields() {
    const action = document.getElementById('adminAction').value;
    const oldNameRow = document.getElementById('oldNameRow');
    const newNameRow = document.getElementById('newNameRow');
    const employeeIdRow = document.getElementById('employeeIdRow');
    const phoneRow = document.getElementById('phoneRow');
    
    switch(action) {
        case 'add':
            // 补签：只需要新信息
            oldNameRow.style.display = 'none';
            newNameRow.style.display = 'flex';
            employeeIdRow.style.display = 'flex';
            phoneRow.style.display = 'flex';
            break;
        case 'modify':
            // 修改：需要原姓名和新信息
            oldNameRow.style.display = 'flex';
            newNameRow.style.display = 'flex';
            employeeIdRow.style.display = 'flex';
            phoneRow.style.display = 'flex';
            break;
        case 'delete':
            // 删除：只需要原姓名
            oldNameRow.style.display = 'flex';
            newNameRow.style.display = 'none';
            employeeIdRow.style.display = 'none';
            phoneRow.style.display = 'none';
            break;
    }
}

// 处理签到
async function handleSignIn() {
    // 首先验证IP
    const ipCheck = await verifyIPForSignIn();
    if (!ipCheck.allowed) {
        alert(ipCheck.message);
        return;
    }
    
    const deptCategory = document.getElementById('deptCategory');
    const deptSubItem = document.getElementById('deptSubItem');
    const otherDept = document.getElementById('otherDept');
    const nameInput = document.getElementById('name');
    const employeeIdInput = document.getElementById('employeeId');
    const phoneInput = document.getElementById('phone');
    const latitude = document.getElementById('latitude').value;
    const longitude = document.getElementById('longitude').value;
    const locationAddress = document.getElementById('locationAddress').value;
    
    const category = deptCategory.value;
    if (!category) {
        alert('请选择部门大类！');
        return;
    }
    
    let department;
    if (category === '其他') {
        department = otherDept.value.trim();
        if (!department) {
            alert('请填写具体部门（起重维护/保安/保洁）！');
            return;
        }
    } else {
        const subItem = deptSubItem.value;
        if (!subItem) {
            alert('请选择部门细项！');
            return;
        }
        department = `${category}-${subItem}`;
    }
    
    const name = nameInput.value.trim();
    const employeeId = employeeIdInput.value.trim() || '-';
    const phone = phoneInput.value.trim();
    
    if (!name) {
        alert('请填写姓名！');
        return;
    }
    if (!phone) {
        alert('请填写电话！');
        return;
    }
    
    // 保存记录
    const today = formatDate(new Date());
    
    // 检查该部门是否已签到（从服务器获取最新数据）
    await fetchRecords(today);
    const todayRecords = allRecords[today] || [];
    const existingRecord = todayRecords.find(r => r.department === department);
    const isAlreadySigned = existingRecord && !existingRecord.isDefault;
    
    const record = {
        department,
        name,
        employeeId,
        phone,
        signInTime: new Date().toISOString(),
        latitude: latitude || '',
        longitude: longitude || '',
        location: locationAddress || ''
    };
    
    // 保存到服务器
    const success = await saveRecordToServer(today, record);
    if (!success) return;
    
    if (isAlreadySigned) {
        alert('签到信息已更新！');
    } else {
        alert('签到成功！');
    }
    
    // 重新加载今日记录
    await loadTodayRecords();
    
    // 清空表单
    nameInput.value = '';
    phoneInput.value = '';
}

// 处理管理员操作（补签/修改/删除）
async function handleAdminAction() {
    const action = document.getElementById('adminAction').value;
    const date = document.getElementById('adminDate').value;
    const deptCategory = document.getElementById('adminDeptCategory').value;
    const deptSubItem = document.getElementById('adminDeptSubItem').value;
    const otherDept = document.getElementById('adminOtherDept').value.trim();
    const oldName = document.getElementById('adminOldName').value.trim();
    const newName = document.getElementById('adminNewName').value.trim();
    const newEmployeeId = document.getElementById('adminEmployeeId').value.trim();
    const newPhone = document.getElementById('adminNewPhone').value.trim();
    const password = document.getElementById('adminPassword').value;
    
    // 验证是否是管理员（使用后端返回的权限）
    if (!currentUser || !currentUser.is_admin) {
        alert('权限不足，只有管理员可以执行此操作！');
        return;
    }
    
    // 保留本地密码验证作为二次确认
    if (password !== ADMIN_PASSWORD) {
        alert('管理员密码错误！');
        return;
    }
    
    // 验证部门选择
    if (!deptCategory) {
        alert('请选择部门大类！');
        return;
    }
    
    let department;
    if (deptCategory === '其他') {
        department = otherDept;
        if (!department) {
            alert('请填写具体部门（起重维护/保安/保洁）！');
            return;
        }
    } else {
        if (!deptSubItem) {
            alert('请选择部门细项！');
            return;
        }
        department = `${deptCategory}-${deptSubItem}`;
    }
    
    // 验证必填项
    if (!date) {
        alert('请填写日期！');
        return;
    }
    
    // 从服务器获取最新数据
    await fetchRecords();
    const records = allRecords;
    
    switch(action) {
        case 'add':
            // 补签：新增记录
            if (!newName || !newEmployeeId || !newPhone) {
                alert('补签需要填写姓名、工号和电话！');
                return;
            }
            
            // 如果该日期没有记录，创建空数组
            if (!records[date]) {
                records[date] = [];
            }
            
            // 检查是否已存在相同记录
            const existingIndex = records[date].findIndex(
                r => r.department === department && r.name === newName
            );
            
            const newRecord = {
                department,
                name: newName,
                employeeId: newEmployeeId,
                phone: newPhone,
                signInTime: new Date().toISOString(),
                latitude: '',
                longitude: '',
                location: '管理员补签',
                isAdminAction: true  // 标记为管理员操作，跳过IP限制
            };
            
            // 保存到服务器
            const addSuccess = await saveRecordToServer(date, newRecord);
            if (!addSuccess) return;
            
            if (existingIndex >= 0) {
                alert('该人员已有记录，已更新为补签信息！');
            } else {
                alert('补签成功！');
            }
            break;
            
        case 'modify':
            // 修改：需要原姓名
            if (!oldName) {
                alert('修改操作需要填写原姓名！');
                return;
            }
            if (!records[date]) {
                alert('该日期无签到记录！');
                return;
            }
            
            // 查找原记录
            const modifyIndex = records[date].findIndex(
                r => r.department === department && r.name === oldName
            );
            
            if (modifyIndex < 0) {
                alert('未找到匹配的记录！请检查部门、原姓名是否正确。');
                return;
            }
            
            // 更新记录
            const modifiedRecord = { ...records[date][modifyIndex] };
            if (newName) modifiedRecord.name = newName;
            if (newEmployeeId) modifiedRecord.employeeId = newEmployeeId;
            if (newPhone) modifiedRecord.phone = newPhone;
            modifiedRecord.isModified = true;  // 标记为已修改
            modifiedRecord.isAdminAction = true;  // 标记为管理员操作，跳过IP限制
            
            // 如果姓名改变了，需要先删除旧记录，再添加新记录
            if (newName && newName !== oldName) {
                // 删除旧记录
                const delSuccess = await deleteRecordFromServer(date, department, oldName);
                if (!delSuccess) return;
                // 添加新记录
                const addSuccess2 = await saveRecordToServer(date, modifiedRecord);
                if (!addSuccess2) return;
            } else {
                // 直接更新记录
                const updateSuccess = await saveRecordToServer(date, modifiedRecord);
                if (!updateSuccess) return;
            }
            
            alert('修改成功！');
            break;
            
        case 'delete':
            // 删除：需要原姓名
            if (!oldName) {
                alert('删除操作需要填写原姓名！');
                return;
            }
            if (!records[date]) {
                alert('该日期无签到记录！');
                return;
            }
            
            if (!confirm(`确定要删除 ${date} ${department} ${oldName} 的签到记录吗？`)) {
                return;
            }
            
            // 从服务器删除
            const deleteSuccess = await deleteRecordFromServer(date, department, oldName);
            if (!deleteSuccess) return;
            
            alert('删除成功！');
            break;
    }
    
    // 刷新显示
    if (date === formatDate(new Date())) {
        await loadTodayRecords();
    }
    
    // 清空表单（保留日期和部门）
    document.getElementById('adminOldName').value = '';
    document.getElementById('adminNewName').value = '';
    document.getElementById('adminEmployeeId').value = '';
    document.getElementById('adminNewPhone').value = '';
    document.getElementById('adminPassword').value = '';
    // 注意：部门和日期保留，方便连续操作
}

// 处理清空所有数据
async function handleClearAll() {
    const password = document.getElementById('adminPassword').value;
    
    if (password !== ADMIN_PASSWORD) {
        alert('管理员密码错误！');
        return;
    }
    
    if (!confirm('警告：此操作将清空所有历史签到数据，且无法恢复！\n\n确定要清空吗？')) {
        return;
    }
    
    if (!confirm('再次确认：是否真的要清空所有数据？')) {
        return;
    }
    
    try {
        // 从服务器获取所有记录并删除
        await fetchRecords();
        const records = allRecords;
        
        // 删除所有日期的所有记录
        for (const date of Object.keys(records)) {
            for (const record of records[date]) {
                await deleteRecordFromServer(date, record.department, record.name);
            }
        }
        
        alert('所有数据已清空！');
        
        // 刷新显示
        await loadTodayRecords();
        
        // 清空历史查询结果
        document.getElementById('historyResult').style.display = 'none';
        document.getElementById('historyTableBody').innerHTML = '';
        
        // 清空表单
        document.getElementById('adminPassword').value = '';
    } catch (error) {
        console.error('清空数据失败:', error);
        alert('清空数据失败，请检查网络连接');
    }
}

// 处理历史查询
async function handleQuery() {
    const date = document.getElementById('historyDate').value;
    
    if (!date) {
        alert('请选择查询日期！');
        return;
    }
    
    // 从服务器获取最新数据
    await fetchRecords();
    const dayRecords = allRecords[date] || [];
    
    const resultDiv = document.getElementById('historyResult');
    const tbody = document.getElementById('historyTableBody');
    
    tbody.innerHTML = '';
    
    if (dayRecords.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-message">该日期无签到记录</td></tr>';
    } else {
        dayRecords.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.department}</td>
                <td class="${isLate(record.signInTime) ? 'late-sign' : ''}">${record.name}</td>
                <td>${record.employeeId || ''}</td>
                <td>${record.phone}</td>
                <td>${formatDateTime(new Date(record.signInTime))}</td>
            `;
            tbody.appendChild(row);
        });
    }
    
    resultDiv.style.display = 'block';
}

// 处理导出Excel（按日期）
async function handleExport() {
    const date = document.getElementById('historyDate').value;
    
    if (!date) {
        alert('请先选择要导出的日期！');
        return;
    }
    
    // 从服务器获取最新数据
    await fetchRecords();
    const dayRecords = allRecords[date] || [];
    
    if (dayRecords.length === 0) {
        alert('该日期无签到记录，无法导出！');
        return;
    }
    
    exportToExcel(dayRecords, `南宁公司值班签到表_${date}`);
}

// 处理导出全部数据
async function handleExportAll() {
    // 从服务器获取最新数据
    await fetchRecords();
    const records = allRecords;
    const allData = [];
    
    // 收集所有日期的记录
    for (const [date, dayRecords] of Object.entries(records)) {
        dayRecords.forEach(record => {
            allData.push({
                ...record,
                date: date
            });
        });
    }
    
    if (allData.length === 0) {
        alert('暂无签到记录，无法导出！');
        return;
    }
    
    // 按日期排序
    allData.sort((a, b) => new Date(a.signInTime) - new Date(b.signInTime));
    
    exportToExcel(allData, '南宁公司值班签到表_全部数据');
}

// 导出数据到Excel
function exportToExcel(records, filename) {
    // 准备数据
    const data = records.map(record => {
        const signInDate = new Date(record.signInTime);
        return {
            '日期': record.date || formatDate(signInDate),
            '部门': record.department,
            '姓名': record.name,
            '工号': record.employeeId || '',
            '电话': record.phone,
            '签到时间': formatDateTime(signInDate),
            '是否迟到': isLate(record.signInTime) ? '是' : '否'
        };
    });
    
    // 创建工作簿
    const wb = XLSX.utils.book_new();
    
    // 创建工作表
    const ws = XLSX.utils.json_to_sheet(data);
    
    // 设置列宽
    ws['!cols'] = [
        { wch: 12 },  // 日期
        { wch: 15 },  // 部门
        { wch: 10 },  // 姓名
        { wch: 12 },  // 工号
        { wch: 15 },  // 电话
        { wch: 20 },  // 签到时间
        { wch: 10 }   // 是否迟到
    ];
    
    // 添加工作表到工作簿
    XLSX.utils.book_append_sheet(wb, ws, '签到记录');
    
    // 下载文件
    XLSX.writeFile(wb, `${filename}.xlsx`);
    
    alert(`导出成功！共导出 ${records.length} 条记录`);
}

// ==================== 签到模式管理功能 ====================

// 从服务器加载签到模式设置
async function loadModeSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/mode`);
        if (response.ok) {
            const settings = await response.json();
            signInMode = settings.mode || 'open';
            allowedIPs = settings.allowedIPs || [];
        }
    } catch (error) {
        console.error('加载模式设置失败:', error);
        // 使用默认设置
        signInMode = 'open';
        allowedIPs = [];
    }
    updateModeDisplay();
}

// 保存签到模式设置到服务器
async function saveModeSettings() {
    try {
        const settings = {
            mode: signInMode,
            allowedIPs: allowedIPs
        };
        const response = await fetch(`${API_BASE}/api/mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (!response.ok) throw new Error('保存失败');
        return true;
    } catch (error) {
        console.error('保存模式设置失败:', error);
        return false;
    }
}

// 更新模式显示
function updateModeDisplay() {
    const modeStatus = document.getElementById('modeStatus');
    if (signInMode === 'open') {
        modeStatus.textContent = '当前模式：内网开放';
        modeStatus.classList.remove('restricted');
    } else {
        modeStatus.textContent = '当前模式：限制IP';
        modeStatus.classList.add('restricted');
    }
}

// 获取当前用户IP地址（带超时处理）
async function getCurrentIP() {
    try {
        // 使用 AbortController 设置超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3秒超时
        
        // 使用 ipapi 获取公网IP（免费服务）
        const response = await fetch('https://api.ipify.org?format=json', {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.log('获取外网IP失败（可能是内网环境）:', error.message);
        // 如果获取失败，返回空字符串表示无法获取外网IP
        return '';
    }
}

// 获取本地内网IP（通过WebRTC）
async function getLocalIP() {
    return new Promise((resolve) => {
        try {
            const pc = new RTCPeerConnection({
                iceServers: []
            });
            
            pc.createDataChannel('');
            
            pc.createOffer().then(offer => pc.setLocalDescription(offer));
            
            pc.onicecandidate = (ice) => {
                if (!ice || !ice.candidate || !ice.candidate.candidate) {
                    resolve('');
                    return;
                }
                
                const candidate = ice.candidate.candidate;
                const ipMatch = candidate.match(/(\d+\.\d+\.\d+\.\d+)/);
                if (ipMatch) {
                    resolve(ipMatch[1]);
                } else {
                    resolve('');
                }
                pc.close();
            };
            
            // 3秒超时
            setTimeout(() => {
                resolve('');
                pc.close();
            }, 3000);
        } catch (e) {
            resolve('');
        }
    });
}

// 检测是否为内网IP
function isPrivateIP(ip) {
    // 内网IP段：
    // 10.0.0.0 - 10.255.255.255
    // 172.16.0.0 - 172.31.255.255
    // 192.168.0.0 - 192.168.255.255
    // 127.0.0.0 - 127.255.255.255 (本地回环)
    
    const privateRanges = [
        /^10\./,
        /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
        /^192\.168\./,
        /^127\./,
        /^169\.254\./,  // 链路本地地址
        /^0\./  // 当前网络
    ];
    
    return privateRanges.some(range => range.test(ip));
}

// 验证当前IP是否可以签到
async function verifyIPForSignIn() {
    // 模式一：内网开放 - 允许所有内网IP
    if (signInMode === 'open') {
        const ip = await getCurrentIP();
        currentUserIP = ip;
        
        // 如果是内网IP或无法获取IP，允许签到
        if (!ip || isPrivateIP(ip)) {
            return { allowed: true, message: '' };
        }
        
        // 外网IP，询问是否继续
        return { 
            allowed: confirm(`检测到您使用外网IP (${ip}) 访问，是否继续签到？`), 
            message: '外网IP访问'
        };
    }
    
    // 模式二：限制IP - 只允许指定IP
    if (signInMode === 'restricted') {
        const ip = await getCurrentIP();
        currentUserIP = ip;
        
        // 如果没有设置允许的IP列表，允许所有
        if (!allowedIPs || allowedIPs.length === 0) {
            return { allowed: true, message: '' };
        }
        
        // 检查当前IP是否在允许列表中
        if (allowedIPs.includes(ip)) {
            return { allowed: true, message: '' };
        }
        
        return { 
            allowed: false, 
            message: `当前IP (${ip}) 不在允许签到列表中，请联系管理员添加IP或切换签到模式。`
        };
    }
    
    return { allowed: true, message: '' };
}

// 打开模式设置弹窗
function openModeModal() {
    document.getElementById('modeModal').style.display = 'flex';
    document.getElementById('signInMode').value = signInMode;
    document.getElementById('allowedIPs').value = allowedIPs.join('\n');
    document.getElementById('modeAdminPassword').value = '';
    
    // 显示/隐藏IP设置区域
    toggleIPSettings();
}

// 关闭模式设置弹窗
function closeModeModal() {
    document.getElementById('modeModal').style.display = 'none';
}

// 切换IP设置区域显示
function toggleIPSettings() {
    const mode = document.getElementById('signInMode').value;
    const ipSettings = document.getElementById('ipSettings');
    
    if (mode === 'restricted') {
        ipSettings.style.display = 'block';
    } else {
        ipSettings.style.display = 'none';
    }
}

// 保存模式设置
async function saveModeSettingsFromModal() {
    const password = document.getElementById('modeAdminPassword').value;
    
    if (password !== ADMIN_PASSWORD) {
        alert('管理员密码错误！');
        return;
    }
    
    const newMode = document.getElementById('signInMode').value;
    const ipsText = document.getElementById('allowedIPs').value.trim();
    
    // 解析IP列表
    const newAllowedIPs = ipsText
        .split('\n')
        .map(ip => ip.trim())
        .filter(ip => ip.length > 0);
    
    // 验证IP格式
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    const invalidIPs = newAllowedIPs.filter(ip => !ipRegex.test(ip));
    
    if (invalidIPs.length > 0) {
        alert(`以下IP格式不正确：\n${invalidIPs.join('\n')}\n\n请检查IP格式（如：192.168.1.100）`);
        return;
    }
    
    // 保存设置
    signInMode = newMode;
    allowedIPs = newAllowedIPs;
    const saved = await saveModeSettings();
    
    if (saved) {
        updateModeDisplay();
        alert(`设置已保存！\n当前模式：${newMode === 'open' ? '内网开放' : '限制IP'}\n${newMode === 'restricted' ? `允许IP数：${allowedIPs.length}` : ''}`);
        closeModeModal();
    } else {
        alert('保存设置失败，请检查网络连接');
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
