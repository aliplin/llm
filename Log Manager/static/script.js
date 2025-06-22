// 全局变量
let currentService = 'ssh';
let charts = {};
let realtimeInterval;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    initializeDashboard();
    setupEventListeners();
    loadInitialData();
    startRealtimeUpdates();
});

// 初始化仪表板
function initializeDashboard() {
    console.log('Initializing dashboard...');
    initializeCharts();
    updateLastUpdateTime();
}

// 设置事件监听器
function setupEventListeners() {
    // 刷新按钮
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    // 导出按钮
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportReport);
    }

    // 服务切换按钮
    const serviceButtons = {
        'sshSessionsBtn': 'ssh',
        'httpSessionsBtn': 'http',
        'mysqlSessionsBtn': 'mysql',
        'pop3SessionsBtn': 'pop3'
    };

    Object.keys(serviceButtons).forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', () => switchService(serviceButtons[btnId]));
        }
    });

    // 时间范围选择
    const timeRange = document.getElementById('timeRange');
    if (timeRange) {
        timeRange.addEventListener('change', () => {
            loadServiceData(currentService);
        });
    }

    // 搜索输入
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterTableData);
    }

    // 表格筛选
    const tableFilter = document.getElementById('tableFilter');
    if (tableFilter) {
        tableFilter.addEventListener('change', filterTableData);
    }

    // 日志级别筛选
    const logFilters = document.querySelectorAll('.log-filter');
    logFilters.forEach(filter => {
        filter.addEventListener('click', (e) => {
            logFilters.forEach(f => f.classList.remove('active'));
            e.target.classList.add('active');
            filterLogs(e.target.dataset.level);
        });
    });

    // 模态框关闭
    const modal = document.getElementById('detailModal');
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
}

// 初始化图表
function initializeCharts() {
    // 会话趋势图
    const sessionsTrendCtx = document.getElementById('sessionsTrendChart');
    if (sessionsTrendCtx) {
        charts.sessionsTrend = new Chart(sessionsTrendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '会话数',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // 服务分布图
    const serviceDistributionCtx = document.getElementById('serviceDistributionChart');
    if (serviceDistributionCtx) {
        charts.serviceDistribution = new Chart(serviceDistributionCtx, {
            type: 'doughnut',
            data: {
                labels: ['SSH', 'HTTP', 'MySQL', 'POP3'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#3498db',
                        '#e74c3c',
                        '#f39c12',
                        '#9b59b6'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // 攻击类型统计图
    const attackTypesCtx = document.getElementById('attackTypesChart');
    if (attackTypesCtx) {
        charts.attackTypes = new Chart(attackTypesCtx, {
            type: 'bar',
            data: {
                labels: ['暴力破解', 'SQL注入', 'XSS攻击', '命令注入', '其他'],
                datasets: [{
                    label: '攻击次数',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#e74c3c',
                        '#f39c12',
                        '#f1c40f',
                        '#e67e22',
                        '#95a5a6'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // 地理分布图
    const geoDistributionDiv = document.getElementById('geoDistributionChart');
    if (geoDistributionDiv) {
        charts.geoDistribution = echarts.init(geoDistributionDiv);
        const geoOption = {
            title: {
                text: '攻击源地理分布',
                left: 'center',
                textStyle: {
                    fontSize: 14
                }
            },
            tooltip: {
                trigger: 'item'
            },
            series: [{
                type: 'pie',
                radius: '50%',
                data: [],
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };
        charts.geoDistribution.setOption(geoOption);
    }
}

// 加载初始数据
async function loadInitialData() {
    console.log('Loading initial data...');
    try {
        // 获取概览统计数据
        const statsData = await fetchData('/api/overview-stats');
        updateOverviewStatsFromAPI(statsData);
        
        // 获取图表数据
        const chartData = await fetchData('/api/chart-data');
        updateChartsFromAPI(chartData);
        
        // 获取实时日志
        const logsData = await fetchData('/api/realtime-logs');
        updateRealtimeLogs(logsData);
        
        // 加载当前服务数据
        await loadServiceData(currentService);
    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

// 获取数据
async function fetchData(endpoint) {
    try {
        const response = await fetch(`http://127.0.0.1:5000${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${endpoint}:`, error);
        return [];
    }
}

// 从API更新概览统计
function updateOverviewStatsFromAPI(stats) {
    if (!stats) return;
    
    updateElement('total-sessions', stats.total_sessions || 0);
    updateElement('total-attacks', stats.total_sessions || 0);
    updateElement('active-sessions', stats.total_sessions || 0);
    updateElement('unique-ips', stats.unique_ips || 0);
    updateElement('request-rate', Math.round((stats.total_sessions || 0) / 60));
    updateElement('threat-level', stats.threat_level || '低');
}

// 从API更新图表
function updateChartsFromAPI(chartData) {
    if (!chartData) return;
    
    // 更新服务分布图
    if (charts.serviceDistribution && chartData.service_distribution) {
        charts.serviceDistribution.data.datasets[0].data = chartData.service_distribution.data;
        charts.serviceDistribution.update();
    }
    
    // 更新攻击类型统计
    if (charts.attackTypes && chartData.attack_types) {
        charts.attackTypes.data.datasets[0].data = chartData.attack_types.data;
        charts.attackTypes.update();
    }
    
    // 更新地理分布图
    if (charts.geoDistribution && chartData.geo_distribution) {
        charts.geoDistribution.setOption({
            series: [{
                data: chartData.geo_distribution
            }]
        });
    }
}

// 更新实时日志
function updateRealtimeLogs(logs) {
    const logContainer = document.getElementById('realtimeLogs');
    if (!logContainer || !Array.isArray(logs)) return;
    
    logContainer.innerHTML = '';
    
    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level}`;
        logEntry.dataset.level = log.level;
        
        const icon = getLogIcon(log.level);
        const color = getLogColor(log.level);
        
        logEntry.innerHTML = `
            <div class="log-timestamp">${log.timestamp}</div>
            <div class="log-content">
                <i class="${icon}" style="color: ${color}"></i>
                <span class="log-message">${log.message}</span>
                <span class="log-service">[${log.service}]</span>
            </div>
        `;
        
        logContainer.appendChild(logEntry);
    });
    
    // 滚动到底部
    logContainer.scrollTop = logContainer.scrollHeight;
}

// 获取日志图标
function getLogIcon(level) {
    switch (level) {
        case 'error': return 'fas fa-exclamation-circle';
        case 'warning': return 'fas fa-exclamation-triangle';
        case 'info': return 'fas fa-info-circle';
        default: return 'fas fa-circle';
    }
}

// 获取日志颜色
function getLogColor(level) {
    switch (level) {
        case 'error': return '#e74c3c';
        case 'warning': return '#f39c12';
        case 'info': return '#3498db';
        default: return '#95a5a6';
    }
}

// 切换服务
async function switchService(service) {
    console.log(`Switching to service: ${service}`);
    currentService = service;
    
    // 更新按钮状态
    document.querySelectorAll('.service-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`${service}SessionsBtn`).classList.add('active');
    
    // 加载服务数据
    await loadServiceData(service);
}

// 加载服务数据
async function loadServiceData(service) {
    console.log(`Loading data for service: ${service}`);
    hideAllTables();
    
    try {
        const data = await fetchData(`/${service}_sessions`);
        displayServiceData(service, data);
    } catch (error) {
        console.error(`Error loading ${service} data:`, error);
    }
}

// 显示服务数据
function displayServiceData(service, data) {
    const tableId = `${service}-sessions-table`;
    const table = document.getElementById(tableId);
    
    if (table) {
        table.style.display = 'table';
        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';
        
        if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
                const row = createTableRow(service, item);
                tbody.appendChild(row);
            });
        }
    }
}

// 创建表格行
function createTableRow(service, item) {
    const row = document.createElement('tr');
    
    switch (service) {
        case 'ssh':
            row.innerHTML = `
                <td>${item.id || ''}</td>
                <td>${item.username || ''}</td>
                <td>${formatDateTime(item.time_date) || ''}</td>
                <td>${item.src_ip || ''}</td>
                <td>${item.dst_ip || ''}</td>
                <td>${item.dst_port || ''}</td>
                <td>
                    <button class="action-btn view-btn" onclick="viewSessionDetails('ssh', ${item.id})">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                </td>
            `;
            break;
        case 'http':
            row.innerHTML = `
                <td>${item.id || ''}</td>
                <td>${item.client_ip || ''}</td>
                <td>${formatDateTime(item.start_time) || ''}</td>
                <td>${formatDateTime(item.end_time) || ''}</td>
                <td>${item.request_count || 0}</td>
                <td>
                    <button class="action-btn view-btn" onclick="viewSessionDetails('http', ${item.id})">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                </td>
            `;
            break;
        case 'mysql':
            row.innerHTML = `
                <td>${item.id || ''}</td>
                <td>${item.username || ''}</td>
                <td>${formatDateTime(item.time_date) || ''}</td>
                <td>${item.src_ip || ''}</td>
                <td>${item.database_name || ''}</td>
                <td>${item.command_count || 0}</td>
                <td>
                    <button class="action-btn view-btn" onclick="viewSessionDetails('mysql', ${item.id})">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                </td>
            `;
            break;
        case 'pop3':
            row.innerHTML = `
                <td>${item.id || ''}</td>
                <td>${item.username || ''}</td>
                <td>${formatDateTime(item.time_date) || ''}</td>
                <td>${item.src_ip || ''}</td>
                <td>${item.command_count || 0}</td>
                <td>
                    <button class="action-btn view-btn" onclick="viewSessionDetails('pop3', ${item.id})">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                </td>
            `;
            break;
    }
    
    return row;
}

// 隐藏所有表格
function hideAllTables() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        table.style.display = 'none';
    });
}

// 查看会话详情
async function viewSessionDetails(service, sessionId) {
    try {
        let data;
        switch (service) {
            case 'ssh':
                // SSH会话详情就是会话本身，不需要额外查询
                const sshSessions = await fetchData(`/ssh_sessions`);
                data = sshSessions.find(item => item.id === sessionId);
                break;
            case 'http':
                data = await fetchData(`/http_requests/${sessionId}`);
                break;
            case 'mysql':
                data = await fetchData(`/mysql_commands/${sessionId}`);
                break;
            case 'pop3':
                data = await fetchData(`/pop3_commands/${sessionId}`);
                break;
        }
        
        const content = formatSessionDetails(service, data);
        showModal(`${service.toUpperCase()} 会话详情`, content);
    } catch (error) {
        console.error(`Error fetching ${service} session details:`, error);
        showModal('错误', '获取会话详情失败');
    }
}

// 格式化会话详情
function formatSessionDetails(service, data) {
    if (!data) return '<p>无数据</p>';
    
    let content = '<div class="session-details">';
    
    switch (service) {
        case 'ssh':
            content += `
                <div class="detail-item">
                    <strong>会话ID:</strong> ${data.id || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>用户名:</strong> ${data.username || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>源IP:</strong> ${data.src_ip || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>目标IP:</strong> ${data.dst_ip || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>端口:</strong> ${data.dst_port || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>时间:</strong> ${formatDateTime(data.time_date) || 'N/A'}
                </div>
            `;
            break;
        case 'http':
            if (Array.isArray(data)) {
                content += '<h4>HTTP请求列表:</h4>';
                data.forEach((request, index) => {
                    content += `
                        <div class="request-item">
                            <strong>请求 ${index + 1}:</strong>
                            <div>方法: ${request.method || 'N/A'}</div>
                            <div>路径: ${request.path || 'N/A'}</div>
                            <div>请求时间: ${formatDateTime(request.request_time) || 'N/A'}</div>
                            <div>响应: ${(request.response || '').substring(0, 100)}${(request.response || '').length > 100 ? '...' : ''}</div>
                        </div>
                    `;
                });
            }
            break;
        case 'mysql':
            if (Array.isArray(data)) {
                content += '<h4>MySQL命令列表:</h4>';
                data.forEach((command, index) => {
                    content += `
                        <div class="command-item">
                            <strong>命令 ${index + 1}:</strong>
                            <div>命令: ${command.command || 'N/A'}</div>
                            <div>响应: ${(command.response || '').substring(0, 100)}${(command.response || '').length > 100 ? '...' : ''}</div>
                            <div>命令类型: ${command.command_type || 'N/A'}</div>
                            <div>影响行数: ${command.affected_rows || 0}</div>
                            <div>时间: ${formatDateTime(command.timestamp) || 'N/A'}</div>
                        </div>
                    `;
                });
            }
            break;
        case 'pop3':
            if (Array.isArray(data)) {
                content += '<h4>POP3命令列表:</h4>';
                data.forEach((command, index) => {
                    content += `
                        <div class="command-item">
                            <strong>命令 ${index + 1}:</strong>
                            <div>命令: ${command.command || 'N/A'}</div>
                            <div>响应: ${(command.response || '').substring(0, 100)}${(command.response || '').length > 100 ? '...' : ''}</div>
                            <div>时间: ${formatDateTime(command.timestamp) || 'N/A'}</div>
                        </div>
                    `;
                });
            }
            break;
    }
    
    content += '</div>';
    return content;
}

// 显示模态框
function showModal(title, content) {
    const modal = document.getElementById('detailModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    if (modal && modalTitle && modalBody) {
        modalTitle.textContent = title;
        modalBody.innerHTML = content;
        modal.style.display = 'block';
    }
}

// 关闭模态框
function closeModal() {
    const modal = document.getElementById('detailModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 刷新数据
async function refreshData() {
    console.log('Refreshing data...');
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';
        refreshBtn.disabled = true;
    }
    
    try {
        await loadInitialData();
        updateLastUpdateTime();
    } catch (error) {
        console.error('Error refreshing data:', error);
    } finally {
        if (refreshBtn) {
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 刷新数据';
            refreshBtn.disabled = false;
        }
    }
}

// 导出报告
function exportReport() {
    console.log('Exporting report...');
    // 这里可以实现导出功能
    alert('导出功能开发中...');
}

// 开始实时更新
function startRealtimeUpdates() {
    // 每30秒更新一次数据
    realtimeInterval = setInterval(async () => {
        try {
            // 更新统计数据
            const statsData = await fetchData('/api/overview-stats');
            updateOverviewStatsFromAPI(statsData);
            
            // 更新图表数据
            const chartData = await fetchData('/api/chart-data');
            updateChartsFromAPI(chartData);
            
            // 更新实时日志
            const logsData = await fetchData('/api/realtime-logs');
            updateRealtimeLogs(logsData);
            
            // 更新当前服务数据
            await loadServiceData(currentService);
            
            updateLastUpdateTime();
        } catch (error) {
            console.error('Error in realtime update:', error);
        }
    }, 30000);
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    } catch (error) {
        return dateString;
    }
}

// 更新最后更新时间
function updateLastUpdateTime() {
    const now = new Date();
    updateElement('last-update', now.toLocaleTimeString('zh-CN'));
}

// 更新元素内容
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

// 筛选表格数据
function filterTableData() {
    const searchTerm = document.getElementById('searchInput')?.value.toLowerCase();
    const filterType = document.getElementById('tableFilter')?.value;
    
    const rows = document.querySelectorAll('.data-table tbody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchesSearch = !searchTerm || text.includes(searchTerm);
        const matchesFilter = filterType === 'all' || row.closest('.data-table').id.includes(filterType);
        
        row.style.display = matchesSearch && matchesFilter ? '' : 'none';
    });
}

// 筛选日志
function filterLogs(level) {
    const logs = document.querySelectorAll('#realtimeLogs .log-entry');
    logs.forEach(log => {
        if (level === 'all' || log.dataset.level === level) {
            log.style.display = '';
        } else {
            log.style.display = 'none';
        }
    });
}
