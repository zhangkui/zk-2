export const STATUS_OPTIONS = [
  { value: 'normal', label: '正常', type: 'success' },
  { value: 'opened', label: '已开封', type: 'primary' },
  { value: 'low_stock', label: '低库存', type: 'warning' },
  { value: 'near_expiry', label: '近效期', type: 'danger' },
  { value: 'expired', label: '已过期', type: 'danger' },
  { value: 'scrapped', label: '已报废', type: 'info' },
  { value: 'used_up', label: '已用完', type: 'info' }
]

export const CATEGORY_OPTIONS = [
  { value: 'reagent', label: '试剂' },
  { value: 'consumable', label: '耗材' },
  { value: 'standard', label: '标准品' },
  { value: 'other', label: '其他' }
]

export const OPERATION_TYPE_OPTIONS = [
  { value: 'inbound', label: '入库' },
  { value: 'outbound', label: '领用' },
  { value: 'open', label: '开封' },
  { value: 'return', label: '归还' },
  { value: 'scrap', label: '报废' },
  { value: 'inventory_check', label: '盘点' },
  { value: 'adjust', label: '调整' },
  { value: 'reserve', label: '预占' },
  { value: 'release_reserve', label: '释放预占' },
  { value: 'approve_requisition', label: '审批领用' },
  { value: 'reject_requisition', label: '驳回领用' }
]

export const WARNING_TYPE_OPTIONS = [
  { value: 'near_expiry', label: '近效期', type: 'warning' },
  { value: 'expired', label: '已过期', type: 'danger' },
  { value: 'low_stock', label: '低库存', type: 'warning' }
]

export const WARNING_STATUS_OPTIONS = [
  { value: 'active', label: '待处理', type: 'danger' },
  { value: 'acknowledged', label: '已确认', type: 'warning' },
  { value: 'resolved', label: '已解决', type: 'success' }
]

export const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'manager', label: '管理员' },
  { value: 'operator', label: '操作员' },
  { value: 'viewer', label: '查看员' }
]

export function getStatusLabel(status) {
  const item = STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.label : status
}

export function getStatusType(status) {
  const item = STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.type : 'info'
}

export function getCategoryLabel(category) {
  const item = CATEGORY_OPTIONS.find(o => o.value === category)
  return item ? item.label : category
}

export function getOperationTypeLabel(type) {
  const item = OPERATION_TYPE_OPTIONS.find(o => o.value === type)
  return item ? item.label : type
}

export function getWarningTypeLabel(type) {
  const item = WARNING_TYPE_OPTIONS.find(o => o.value === type)
  return item ? item.label : type
}

export function getWarningTypeTag(type) {
  const item = WARNING_TYPE_OPTIONS.find(o => o.value === type)
  return item ? item.type : 'info'
}

export function getWarningStatusLabel(status) {
  const item = WARNING_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.label : status
}

export function getWarningStatusTag(status) {
  const item = WARNING_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.type : 'info'
}

export function getRoleLabel(role) {
  const item = ROLE_OPTIONS.find(o => o.value === role)
  return item ? item.label : role
}

export const STOCKTAKE_TASK_STATUS_OPTIONS = [
  { value: 'draft', label: '草稿', type: 'info' },
  { value: 'in_progress', label: '进行中', type: 'primary' },
  { value: 'pending_review', label: '待复核', type: 'warning' },
  { value: 'confirmed', label: '已确认', type: 'success' },
  { value: 'closed', label: '已关闭', type: 'info' }
]

export const STOCKTAKE_ITEM_STATUS_OPTIONS = [
  { value: 'not_entered', label: '未录入', type: 'info' },
  { value: 'saved', label: '已暂存', type: 'primary' },
  { value: 'submitted', label: '已提交', type: 'warning' },
  { value: 'confirmed', label: '已确认', type: 'success' }
]

export function getStocktakeTaskLabel(status) {
  const item = STOCKTAKE_TASK_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.label : status
}

export function getStocktakeTaskType(status) {
  const item = STOCKTAKE_TASK_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.type : 'info'
}

export function getStocktakeItemLabel(status) {
  const item = STOCKTAKE_ITEM_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.label : status
}

export function getStocktakeItemType(status) {
  const item = STOCKTAKE_ITEM_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.type : 'info'
}

export const REQUISITION_STATUS_OPTIONS = [
  { value: 'pending', label: '待审批', type: 'warning' },
  { value: 'approved', label: '已通过', type: 'success' },
  { value: 'rejected', label: '已驳回', type: 'danger' },
  { value: 'cancelled', label: '已取消', type: 'info' }
]

export function getRequisitionStatusLabel(status) {
  const item = REQUISITION_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.label : status
}

export function getRequisitionStatusType(status) {
  const item = REQUISITION_STATUS_OPTIONS.find(o => o.value === status)
  return item ? item.type : 'info'
}
