# 接口文档

## 基础信息

- Base URL: `/api`
- 认证方式: Bearer Token (JWT)
- 数据格式: JSON

## 1. 认证接口

### 1.1 登录

```
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded
```

请求参数：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 1.2 获取当前用户

```
GET /api/auth/me
Authorization: Bearer <token>
```

### 1.3 修改密码

```
POST /api/auth/change-password
Authorization: Bearer <token>
```

请求体：
```json
{
  "old_password": "原密码",
  "new_password": "新密码(至少6位)"
}
```

## 2. 物料管理接口

### 2.1 获取物料列表

```
GET /api/admin/materials
```

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| category | string | 分类：reagent/consumable/standard/other |
| is_active | boolean | 是否启用 |
| keyword | string | 搜索关键字（编码/名称） |

### 2.2 获取物料详情

```
GET /api/admin/materials/{id}
```

### 2.3 创建物料

```
POST /api/admin/materials
权限：admin, manager
```

请求体：
```json
{
  "code": "MAT001",
  "name": "乙醇",
  "category": "reagent",
  "specification": "500ml",
  "unit": "瓶",
  "manufacturer": "国药集团",
  "min_stock": 5,
  "open_validity_days": 30,
  "description": "分析纯"
}
```

### 2.4 更新物料

```
PUT /api/admin/materials/{id}
权限：admin, manager
```

## 3. 库存管理接口

### 3.1 获取库存列表

```
GET /api/inventory
```

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| material_id | int | 物料ID |
| status | string | 状态筛选 |
| keyword | string | 搜索关键字 |
| only_expired | boolean | 只看已过期 |
| only_near_expiry | boolean | 只看近效期 |

响应示例：
```json
[
  {
    "id": 1,
    "material_id": 1,
    "material": { "...": "物料对象" },
    "batch_no": "BATCH20240101",
    "quantity": 10,
    "original_expiry_date": "2025-12-31T23:59:59",
    "open_time": null,
    "opened": false,
    "status": "normal",
    "actual_expiry_date": "2025-12-31T23:59:59",
    "location": "A-01"
  }
]
```

### 3.2 新增入库

```
POST /api/inventory
权限：admin, manager, operator
```

请求体：
```json
{
  "material_id": 1,
  "batch_no": "BATCH20240101",
  "quantity": 10,
  "original_expiry_date": "2025-12-31T23:59:59",
  "location": "A-01",
  "remark": "首批入库"
}
```

### 3.3 开封操作

```
POST /api/inventory/{id}/open
权限：admin, manager, operator
```

约束：
- 不可重复开封
- 已报废库存不可开封

请求体：
```json
{
  "remark": "备注"
}
```

### 3.4 领用操作

```
POST /api/inventory/{id}/outbound
权限：admin, manager, operator
```

约束：
- 已过期禁止领用
- 已报废禁止领用
- 领用数量不超过当前库存

请求体：
```json
{
  "inventory_item_id": 1,
  "operation_type": "outbound",
  "quantity_change": 3,
  "remark": "实验使用"
}
```

### 3.5 归还操作

```
POST /api/inventory/{id}/return
权限：admin, manager, operator
```

请求体：同领用操作，quantity_change 为正数

### 3.6 报废操作

```
POST /api/inventory/{id}/scrap
权限：admin, manager
```

请求体：
```json
{
  "inventory_item_id": 1,
  "operation_type": "scrap",
  "quantity_change": 5,
  "remark": "变质报废"
}
```

说明：quantity_change 填最大数量或 0 表示全部报废

### 3.7 盘点操作

```
POST /api/inventory/{id}/inventory-check
权限：admin, manager, operator
```

请求体：
```json
{
  "inventory_item_id": 1,
  "operation_type": "inventory_check",
  "quantity_change": 8,
  "remark": "月度盘点"
}
```

说明：quantity_change 为实际盘点数量

### 3.8 获取库存操作记录

```
GET /api/inventory/{id}/operations
```

## 4. 预警与监控接口

### 4.1 获取预警列表

```
GET /api/warnings
```

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| warning_type | string | near_expiry/expired/low_stock |
| status | string | active/acknowledged/resolved |

### 4.2 处理预警

```
PUT /api/warnings/{id}
权限：admin, manager, operator
```

请求体：
```json
{
  "status": "acknowledged",
  "handled_remark": "已通知相关人员"
}
```

### 4.3 手动触发预警扫描

```
GET /api/warnings/scan
权限：admin, manager
```

### 4.4 获取操作记录

```
GET /api/operations
```

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| operation_type | string | 操作类型筛选 |
| operator_id | int | 操作人ID |
| start_date | datetime | 开始时间 |
| end_date | datetime | 结束时间 |
| limit | int | 返回数量，默认100，最大1000 |

### 4.5 获取仪表盘统计

```
GET /api/dashboard/stats
```

响应：
```json
{
  "total_materials": 50,
  "total_inventory": 120,
  "total_warnings": 8,
  "near_expiry_count": 3,
  "expired_count": 2,
  "low_stock_count": 3,
  "total_operations_today": 15
}
```

## 5. 用户管理接口（管理员）

### 5.1 获取用户列表

```
GET /api/admin/users
权限：admin
```

### 5.2 创建用户

```
POST /api/admin/users
权限：admin
```

请求体：
```json
{
  "username": "zhangsan",
  "full_name": "张三",
  "email": "zhangsan@example.com",
  "role": "operator",
  "password": "password123"
}
```

### 5.3 更新用户

```
PUT /api/admin/users/{id}
权限：admin
```

## 6. 角色权限说明

| 角色 | 权限 |
|------|------|
| admin | 所有权限 |
| manager | 物料/库存管理、预警处理、报废操作 |
| operator | 入库、开封、领用、归还、盘点、预警处理 |
| viewer | 仅查看权限 |

## 7. 状态/枚举值参考

### 库存状态 (InventoryStatus)
- normal, opened, low_stock, near_expiry, expired, scrapped, used_up

### 操作类型 (OperationType)
- inbound（入库）, outbound（领用）, open（开封）, return（归还）, scrap（报废）, inventory_check（盘点）, adjust（调整）

### 预警类型 (WarningType)
- near_expiry, expired, low_stock

### 预警状态 (WarningStatus)
- active, acknowledged, resolved

### 用户角色 (UserRole)
- admin, manager, operator, viewer

### 物料分类 (MaterialCategory)
- reagent, consumable, standard, other
