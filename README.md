# OpenClaw Admin UI

OpenClaw 智能助手平台的企业级后台管理系统，将 Agent 视为真实员工进行管理。

---

## 核心功能

### 员工管理
- **员工卡片**：以卡片形式展示所有 Agent 员工
- **绩效排行**：基于任务完成情况的员工排名

### 工作台（仪表盘）
- **任务统计**：今日任务、完成率、平均耗时、进行中
- **工作趋势**：7天工作趋势图表
- **类型分布**：报告、文档、代码等任务类型分布
- **最近工作**：最近完成的任务列表

### 系统管理
- **Agent 管理**：创建、编辑、删除 Agent
- **绑定配置**：管理 Agent 与渠道的绑定关系
- **工具配置**：查看和配置 Agent 工具权限
- **模型配置**：查看可用模型列表

### 运维监控
- **运行状态**：监控 Gateway 运行状态
- **会话列表**：查看当前活跃会话
- **操作日志**：查看系统操作日志
- **配置管理**：查看和编辑配置

### 权限安全
- **用户管理**：多用户管理（admin/operator/viewer）
- **角色权限**：RBAC 权限控制
- **安全设置**：密码修改、登录审计

---

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.8+
- 虚拟环境：`/home/iamlibai/workspace/python_env_common`

### 启动方式

```bash
# 方式一：使用启动脚本
./start.sh

# 方式二：手动启动
# 后端
cd backend
source /home/iamlibai/workspace/python_env_common/bin/activate
python app.py

# 前端
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端 UI：http://localhost:5000
- 后端 API：http://127.0.0.1:5001

### 默认账户
- 用户名：`admin`
- 密码：`admin123`

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 组件 | Element Plus |
| 状态管理 | Pinia |
| 图表 | ECharts |
| 后端框架 | Python Flask |
| 数据库 | SQLite |
| 认证 | JWT |
| 权限 | RBAC |

---

## 目录结构

```
openclaw-control-ui/
├── backend/               # 后端代码
│   ├── app.py            # Flask 主应用
│   ├── database.py       # 数据库管理
│   ├── auth.py           # JWT 认证
│   ├── decorators.py     # 权限装饰器
│   └── config_manager.py # 配置管理
│
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── api/          # API 接口
│   │   ├── stores/       # Pinia 状态
│   │   ├── router/       # 路由配置
│   │   └── assets/       # 静态资源
│   └── package.json
│
├── docs/                  # 项目文档
│   ├── 01-产品规划/       # 路线图、版本计划
│   ├── 02-需求设计/       # 功能设计文档
│   ├── 03-技术架构/       # 架构、API 文档
│   ├── 04-开发规范/       # 编码规范
│   ├── 05-测试文档/       # 测试相关
│   ├── 06-部署运维/       # 部署、运维
│   └── 07-会议记录/       # 讨论记录
│
└── README.md
```

---

## 文档导航

| 文档 | 路径 |
|------|------|
| 产品路线图 | [docs/01-产品规划/产品路线图.md](docs/01-产品规划/产品路线图.md) |
| 版本计划 | [docs/01-产品规划/版本计划.md](docs/01-产品规划/版本计划.md) |
| 首页仪表盘设计 | [docs/02-需求设计/首页仪表盘设计.md](docs/02-需求设计/首页仪表盘设计.md) |
| 系统架构 | [docs/03-技术架构/系统架构.md](docs/03-技术架构/系统架构.md) |
| API 接口文档 | [docs/03-技术架构/API接口文档.md](docs/03-技术架构/API接口文档.md) |
| 编码规范 | [docs/04-开发规范/编码规范.md](docs/04-开发规范/编码规范.md) |

---

## 权限矩阵

| 功能 | admin | operator | viewer |
|------|:-----:|:--------:|:------:|
| Agent 管理 | ✓ | ✓ | 只读 |
| 员工管理 | ✓ | ✓ | 只读 |
| 用户管理 | ✓ | - | - |
| 配置编辑 | ✓ | 只读 | 只读 |
| Gateway 控制 | ✓ | ✓ | - |

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-03-30 | 基础框架完成 |
| v1.1.0 | 开发中 | 首页仪表盘 |