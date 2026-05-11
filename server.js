const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

// 数据文件路径
const DATA_FILE = path.join(__dirname, 'data.json');
const MODE_FILE = path.join(__dirname, 'mode.json');

// 确保数据文件存在
function initDataFiles() {
    if (!fs.existsSync(DATA_FILE)) {
        fs.writeFileSync(DATA_FILE, JSON.stringify({}), 'utf8');
    }
    if (!fs.existsSync(MODE_FILE)) {
        fs.writeFileSync(MODE_FILE, JSON.stringify({
            mode: 'open',
            allowedIPs: []
        }), 'utf8');
    }
}

// 读取签到数据
function readData() {
    try {
        const data = fs.readFileSync(DATA_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        return {};
    }
}

// 保存签到数据
function saveData(data) {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
}

// 读取模式设置
function readMode() {
    try {
        const data = fs.readFileSync(MODE_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        return { mode: 'open', allowedIPs: [] };
    }
}

// 保存模式设置
function saveMode(mode) {
    fs.writeFileSync(MODE_FILE, JSON.stringify(mode, null, 2), 'utf8');
}

// 获取客户端IP
function getClientIP(req) {
    return req.headers['x-forwarded-for'] ||
           req.connection.remoteAddress ||
           req.socket.remoteAddress ||
           req.connection.socket.remoteAddress;
}

// MIME类型映射
const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

// 创建HTTP服务器
const server = http.createServer((req, res) => {
    // 设置CORS头，允许跨域访问
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;

    // API路由
    if (pathname === '/api/records') {
        handleRecordsAPI(req, res);
        return;
    }

    if (pathname === '/api/mode') {
        handleModeAPI(req, res);
        return;
    }

    if (pathname === '/api/ip') {
        // 返回客户端IP
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ip: getClientIP(req) }));
        return;
    }

    // 静态文件服务
    let filePath = pathname === '/' ? '/index.html' : pathname;
    filePath = path.join(__dirname, filePath);

    const ext = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/plain' });
                res.end('文件未找到');
            } else {
                res.writeHead(500);
                res.end('服务器错误: ' + error.code);
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

// 处理签到记录API
function handleRecordsAPI(req, res) {
    const method = req.method;

    if (method === 'GET') {
        // 获取所有记录
        const data = readData();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
        return;
    }

    if (method === 'POST') {
        // 添加或更新记录
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            try {
                const { date, record } = JSON.parse(body);
                const data = readData();

                if (!data[date]) {
                    data[date] = [];
                }

                // 检查是否已存在相同记录（同部门同名）
                const existingIndex = data[date].findIndex(
                    r => r.department === record.department && r.name === record.name
                );

                if (existingIndex >= 0) {
                    // 更新已有记录
                    data[date][existingIndex] = record;
                } else {
                    // 添加新记录
                    data[date].push(record);
                }

                saveData(data);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (error) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: '数据格式错误' }));
            }
        });
        return;
    }

    if (method === 'DELETE') {
        // 删除记录
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            try {
                const { date, department, name } = JSON.parse(body);
                const data = readData();

                if (data[date]) {
                    data[date] = data[date].filter(
                        r => !(r.department === department && r.name === name)
                    );

                    // 如果该日期没有记录了，删除该日期
                    if (data[date].length === 0) {
                        delete data[date];
                    }

                    saveData(data);
                }

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (error) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: '数据格式错误' }));
            }
        });
        return;
    }

    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: '方法不允许' }));
}

// 处理模式设置API
function handleModeAPI(req, res) {
    const method = req.method;

    if (method === 'GET') {
        // 获取模式设置
        const mode = readMode();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(mode));
        return;
    }

    if (method === 'POST') {
        // 保存模式设置
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            try {
                const mode = JSON.parse(body);
                saveMode(mode);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } catch (error) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: '数据格式错误' }));
            }
        });
        return;
    }

    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: '方法不允许' }));
}

// 初始化数据文件
initDataFiles();

// 启动服务器
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
    console.log(`局域网访问请使用本机IP: http://<本机IP>:${PORT}`);
});
