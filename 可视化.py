import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

# 中文配置
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False
import plotly.express as px

# 数据定义
labels = [
    '管理员访问权限获取', '普通用户访问权限获取', '未授权的信息泄露',
    '未授权的信息修改', '拒绝服务', '其它', '未知'
]
sizes = [29.3, 0.9, 41.5, 13.3, 14.6, 0.5, 0.1]

# 创建3D饼图
fig = px.pie(
    names=labels,
    values=sizes,
    title='截止2025-6-20的CNVD按漏洞引发威胁统计的漏洞分布图',
    hole=0.2,  # 中间空心增强3D感
)

# 配置样式：增大百分比文字、设置颜色、添加边框
fig.update_traces(
    textposition='outside',  # 百分比显示在外侧
    textinfo='percent+label',  # 同时显示百分比和标签
    marker=dict(
        line=dict(color='white', width=2)  # 扇形边框
    ),
    textfont=dict(size=20),  # 增大百分比文字大小
)

# 调整布局
fig.update_layout(
    font=dict(family="SimHei", size=14),  # 确保中文正常显示
    title=dict(font=dict(size=20)),  # 增大标题字体
    margin=dict(t=80, b=20, l=20, r=20),  # 调整边距
    legend=dict(
        title='<b>漏洞类型</b>',
        orientation='v',        # 垂直布局
        yanchor='top',          # 图例顶部对齐
        y=20,                  # 图例垂直位置（左下角）
        xanchor='left',         # 图例左侧对齐
        x=19,                  # 图例水平位置（左下角）
        bgcolor='rgba(255, 255, 255, 0.7)',  # 半透明背景
        bordercolor='rgba(0, 0, 0, 0.1)',
        borderwidth=1,
        font=dict(size=18)       # 图例文字大小
    ),
)

fig.show()