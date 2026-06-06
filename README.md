# 试剂/耗材效期追踪系统

## 项目概述

本系统是一个完整的试剂/耗材效期追踪管理系统，用于实验室或医疗机构对试剂、耗材的库存、效期进行全生命周期管理。

## 技术栈

### 前端
- Vue 3 + Composition API
- Element Plus UI 组件库
- Pinia 状态管理
- Vue Router 路由
- Axios HTTP 客户端

### 后端
- FastAPI (Python 3.11+)
- SQLAlchemy 2.0 ORM
- Pydantic 数据验证
- PostgreSQL 数据库
- JWT 身份认证
- APScheduler 定时任务

## 功能特性

### 核心功能
- **物料主数据管理**：管理试剂/耗材的基础信息、分类、规格
- **批次库存管理**：管理每个批次的入库、数量、原始有效期
- **开封管理**：记录开封时间，自动计算开封后失效时间
- **预警中心**：近效期预警、过期预警、低库存预警
- **操作留痕**：领用、归还、报废、盘点等操作记录
- **用户权限**：多角色权限管理

### 业务规则
- 实际失效时间 = min(原始有效期, 开封时间 + 开封后有效期)
- 已过期物料禁止领用
- 同一库存实例只能开封一次
- 低于最低库存阈值自动预警
- 报废后库存不可再参与任何操作

## 快速开始

### 使用 Docker Compose 启动

```bash
docker-compose up -d
```

访问前端：http://localhost
访问后端 API 文档：http://localhost:8000/docs

### 默认账户
- 用户名：admin
- 密码：admin123

## 文档

详细文档请参考 `docs/` 目录：
- [效期计算说明](docs/expiry_calculation.md)
- [库存状态流转说明](docs/inventory_status_flow.md)
- [接口文档](docs/api_documentation.md)

## 测试

运行后端测试：
```bash
cd backend
pytest tests/ -v
```
