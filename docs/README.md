# 文档目录 / Documentation Index

[English](#english) | [中文](#中文)

---

## English

### Documentation Hierarchy

```
Level 1 — Getting Started
├── [Quick Start Guide](QUICK_START.md)           # First-time setup
└── [Deployment Guide](DEPLOYMENT.md)            # Docker deployment details

Level 2 — User Guides
├── [User Guide](USER_GUIDE.md)                  # Feature usage
└── [Troubleshooting Guide](TROUBLESHOOTING.md)  # FAQ and problem solving

Level 3 — Reference
├── [API Registry](../stock-fast-api/docs/REGISTRY.md)              # Complete API (42 endpoints) — authoritative source
├── [Database Design](../stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md)  # Schema and table design
├── [Architecture Design](../stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md)  # System architecture
└── [Table Relationships](../stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md)  # Table associations

Level 4 — Operational
├── [DDL Script Reference](DDL_REFERENCE.md)    # SQL initialization script guide
├── [Scheduled Tasks](../stock-fast-api/docs/定时任务使用文档.md)              # ETL task configuration
└── [Frontend Architecture](../stock-front_ui/docs/A股股票信息缓存系统前端架构设计文档.md)  # Frontend design
```

### Documentation List

| Document | Description |
|----------|-------------|
| [Quick Start Guide](QUICK_START.md) | Getting started with Docker Compose or manual setup |
| [User Guide](USER_GUIDE.md) | How to use each feature (screening, stock analysis, etc.) |
| [Deployment Guide](DEPLOYMENT.md) | Detailed Docker Compose deployment |
| [Troubleshooting Guide](TROUBLESHOOTING.md) | FAQ and common problem solutions |
| [DDL Script Reference](DDL_REFERENCE.md) | Database initialization script guide |
| [API Registry](../stock-fast-api/docs/REGISTRY.md) | Complete API documentation (42 endpoints) — **primary source** |
| [Database Design](../stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md) | Database schema and table design |
| [Table Relationships](../stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md) | Table association diagrams |
| [Architecture Design](../stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md) | System architecture and data flow |
| [Scheduled Tasks](../stock-fast-api/docs/定时任务使用文档.md) | ETL task configuration and management |
| [Frontend Architecture](../stock-front_ui/docs/A股股票信息缓存系统前端架构设计文档.md) | Frontend system design |

---

## 中文

### 文档层级结构

```
一级 — 快速开始
├── [快速入门指南](QUICK_START.md)          # 首次安装部署
└── [部署指南](DEPLOYMENT.md)              # Docker 部署详解

二级 — 用户指南
├── [用户使用指南](USER_GUIDE.md)          # 功能使用方法
└── [故障排查指南](TROUBLESHOOTING.md)     # 常见问题与解决方案

三级 — 参考文档
├── [API 接口文档](../stock-fast-api/docs/REGISTRY.md)                          # 完整 API（42端点）— **权威来源**
├── [数据库设计文档](../stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md)  # 数据库表结构
├── [表关系说明](../stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md)     # 表之间关联
└── [架构设计文档](../stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md)      # 系统架构与数据流

四级 — 运维指南
├── [DDL 脚本参考](DDL_REFERENCE.md)                                        # 数据库初始化脚本说明
├── [定时任务使用文档](../stock-fast-api/docs/定时任务使用文档.md)             # ETL 任务配置管理
└── [前端架构设计文档](../stock-front_ui/docs/A股股票信息缓存系统前端架构设计文档.md)  # 前端系统设计
```

### 文档列表

| 文档 | 说明 |
|------|------|
| [快速入门指南](QUICK_START.md) | Docker Compose 或手动部署快速开始 |
| [用户使用指南](USER_GUIDE.md) | 各功能使用方法（选股、个股分析等） |
| [部署指南](DEPLOYMENT.md) | Docker Compose 详细部署步骤 |
| [故障排查指南](TROUBLESHOOTING.md) | 常见问题与解决方案 |
| [DDL 脚本参考](DDL_REFERENCE.md) | 数据库 DDL 脚本说明 |
| [API 接口文档](../stock-fast-api/docs/REGISTRY.md) | 完整 API 文档（42 个端点）— **权威来源** |
| [数据库设计文档](../stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md) | 数据库表结构设计 |
| [表关系说明](../stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md) | 表之间关联关系 |
| [架构设计文档](../stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md) | 系统架构与数据流 |
| [定时任务使用文档](../stock-fast-api/docs/定时任务使用文档.md) | ETL 任务配置管理 |
| [前端架构设计文档](../stock-front_ui/docs/A股股票信息缓存系统前端架构设计文档.md) | 前端系统设计 |

---

## Quick Links / 快速链接

- **GitHub Repository**: https://github.com/myliuyx/stock_project
- **API Documentation**: http://localhost:8000/docs (local)
- **Issue Tracker**: https://github.com/myliuyx/stock_project/issues