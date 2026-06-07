<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">库存管理</h2>
      <el-button type="primary" @click="handleAdd" v-if="canEdit">
        <el-icon><Plus /></el-icon>新增入库
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="物料">
          <el-select
            v-model="filters.material_id"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="m in materials"
              :key="m.id"
              :label="`${m.code} - ${m.name}`"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in STATUS_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="物料/批次号"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="filters.only_expired">只看已过期</el-checkbox>
          <el-checkbox v-model="filters.only_near_expiry">只看近效期</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="resetFilter">
            <el-icon><RefreshLeft /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-container">
      <el-table :data="inventory" v-loading="loading" stripe :row-class-name="rowClass">
        <el-table-column label="物料编码" width="110">
          <template #default="{ row }">
            {{ row.material?.code }}
          </template>
        </el-table-column>
        <el-table-column label="物料名称" width="140">
          <template #default="{ row }">
            {{ row.material?.name }}
          </template>
        </el-table-column>
        <el-table-column label="批次号" prop="batch_no" width="140" />
        <el-table-column label="实际数量" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.quantity <= (row.material?.min_stock || 0) ? 'status-low_stock' : ''">
              {{ row.quantity }} {{ row.material?.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="预占数量" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.reserved_quantity > 0" class="status-warning">
              {{ row.reserved_quantity }} {{ row.material?.unit }}
            </span>
            <span v-else style="color: #909399;">
              -
            </span>
          </template>
        </el-table-column>
        <el-table-column label="可用数量" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.available_quantity <= (row.material?.min_stock || 0) ? 'status-low_stock' : ''" :style="{ fontWeight: 'bold' }">
              {{ row.available_quantity }} {{ row.material?.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="原始有效期" width="140">
          <template #default="{ row }">
            {{ formatDate(row.original_expiry_date) }}
          </template>
        </el-table-column>
        <el-table-column label="开封时间" width="140">
          <template #default="{ row }">
            {{ row.open_time ? formatDate(row.open_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="实际失效日期" width="150">
          <template #default="{ row }">
            <span :class="getStatusClass(row.status)">
              {{ formatDate(row.actual_expiry_date) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="存放位置" prop="location" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :class="`tag-${row.status}`" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="cmd => handleOperation(cmd, row)">
              <el-button type="primary" size="small">
                操作 <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="open" :disabled="row.opened || row.status === 'scrapped'">
                    <el-icon><Unlock /></el-icon>开封
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="outbound"
                    :disabled="row.status === 'scrapped' || row.status === 'expired' || row.available_quantity <= 0"
                  >
                    <el-icon><Minus /></el-icon>领用
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="reserve"
                    :disabled="row.status === 'scrapped' || row.status === 'expired' || row.available_quantity <= 0 || row.status === 'used_up'"
                  >
                    <el-icon><Lock /></el-icon>预占
                  </el-dropdown-item>
                  <el-dropdown-item command="return" :disabled="row.status === 'scrapped'">
                    <el-icon><RefreshLeft /></el-icon>归还
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="scrap"
                    :disabled="row.status === 'scrapped'"
                    divided
                  >
                    <el-icon><Delete /></el-icon>报废
                  </el-dropdown-item>
                  <el-dropdown-item command="check" :disabled="row.status === 'scrapped'">
                    <el-icon><Finished /></el-icon>盘点
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button type="primary" link size="small" @click="viewTimeline(row)">
              <el-icon><Clock /></el-icon>时间轴
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="addDialogVisible"
      title="新增入库"
      width="600px"
      @close="resetAddForm"
    >
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="120px">
        <el-form-item label="物料" prop="material_id">
          <el-select v-model="addForm.material_id" filterable style="width: 100%">
            <el-option
              v-for="m in materials"
              :key="m.id"
              :label="`${m.code} - ${m.name}`"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="批次号" prop="batch_no">
              <el-input v-model="addForm.batch_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="入库数量" prop="quantity">
              <el-input-number v-model="addForm.quantity" :min="0.01" step="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="原始有效期" prop="original_expiry_date">
              <el-date-picker
                v-model="addForm.original_expiry_date"
                type="datetime"
                style="width: 100%"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="存放位置">
              <el-input v-model="addForm.location" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="addForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddSubmit">确认入库</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="opDialogVisible"
      :title="opDialogTitle"
      width="450px"
      @close="resetOpForm"
    >
      <el-form :model="opForm" label-width="100px">
        <el-form-item label="物料">
          <span>{{ currentItem?.material?.name }}</span>
        </el-form-item>
        <el-form-item label="批次">
          <span>{{ currentItem?.batch_no }}</span>
        </el-form-item>
        <el-form-item label="可用数量" v-if="opType === 'reserve'">
          <span>{{ currentItem?.available_quantity }} {{ currentItem?.material?.unit }}</span>
        </el-form-item>
        <el-form-item v-if="opType !== 'open' && opType !== 'scrap'" label="数量">
          <el-input-number
            v-model="opForm.quantity_change"
            :min="0.01"
            :max="opType === 'reserve' ? (currentItem?.available_quantity || 0.01) : undefined"
            step="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="opType === 'check'" label="实际数量">
          <el-input-number
            v-model="opForm.quantity_change"
            :min="0"
            step="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="opType === 'scrap'" label="报废数量">
          <el-input-number
            v-model="opForm.quantity_change"
            :min="0.01"
            :max="currentItem?.quantity || 0"
            step="1"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 4px;">
            留空或填最大数量则全部报废
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="opForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="opDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleOpSubmit">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="timelineVisible" title="操作时间轴" width="600px">
      <el-timeline>
        <el-timeline-item
          v-for="op in operations"
          :key="op.id"
          :timestamp="formatDate(op.operation_time)"
          placement="top"
        >
          <el-card shadow="never">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <el-tag size="small">{{ getOperationTypeLabel(op.operation_type) }}</el-tag>
              <span style="color: #909399; font-size: 12px;">
                {{ op.operator?.full_name }}
              </span>
            </div>
            <div v-if="op.quantity_change !== 0" style="margin-top: 8px;">
              数量变化：
              <span :class="op.quantity_change > 0 ? 'status-normal' : 'status-low_stock'">
                {{ op.quantity_change > 0 ? '+' : '' }}{{ op.quantity_change }}
              </span>
              （{{ op.quantity_before }} → {{ op.quantity_after }}）
            </div>
            <div v-if="op.remark" style="margin-top: 8px; color: #606266;">
              {{ op.remark }}
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="!operations.length" description="暂无操作记录" :image-size="80" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { listMaterials } from '@/api/admin'
import {
  listInventory, createInventory, openInventory,
  outboundInventory, returnInventory, scrapInventory,
  inventoryCheck, getInventoryOperations,
  reserveInventory
} from '@/api/inventory'
import {
  STATUS_OPTIONS, getStatusLabel, getOperationTypeLabel
} from '@/utils/dict'

const route = useRoute()
const userStore = useUserStore()
const canEdit = computed(() => ['admin', 'manager', 'operator'].includes(userStore.userInfo?.role))

const loading = ref(false)
const inventory = ref([])
const materials = ref([])

const filters = reactive({
  material_id: route.query.material_id ? Number(route.query.material_id) : '',
  status: '',
  keyword: '',
  only_expired: false,
  only_near_expiry: false
})

const addDialogVisible = ref(false)
const addFormRef = ref(null)
const defaultAddForm = {
  material_id: '',
  batch_no: '',
  quantity: 1,
  original_expiry_date: '',
  location: '',
  remark: ''
}
const addForm = reactive({ ...defaultAddForm })
const addRules = {
  material_id: [{ required: true, message: '请选择物料', trigger: 'change' }],
  batch_no: [{ required: true, message: '请输入批次号', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  original_expiry_date: [{ required: true, message: '请选择有效期', trigger: 'change' }]
}

const opDialogVisible = ref(false)
const opType = ref('')
const currentItem = ref(null)
const opForm = reactive({ quantity_change: 1, remark: '' })

const timelineVisible = ref(false)
const operations = ref([])

const opDialogTitle = computed(() => {
  const map = {
    open: '开封操作',
    outbound: '领用操作',
    reserve: '预占操作',
    return: '归还操作',
    scrap: '报废操作',
    check: '盘点操作'
  }
  return map[opType.value] || '操作'
})

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

function rowClass({ row }) {
  return `status-${row.status}`
}

function getStatusClass(status) {
  if (status === 'expired') return 'status-expired'
  if (status === 'near_expiry') return 'status-near_expiry'
  return ''
}

async function fetchMaterials() {
  try {
    materials.value = await listMaterials({ is_active: true })
  } catch (e) {}
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filters.material_id) params.material_id = filters.material_id
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.only_expired) params.only_expired = true
    if (filters.only_near_expiry) params.only_near_expiry = true
    inventory.value = await listInventory(params)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filters.material_id = ''
  filters.status = ''
  filters.keyword = ''
  filters.only_expired = false
  filters.only_near_expiry = false
  fetchData()
}

function handleAdd() {
  Object.assign(addForm, defaultAddForm)
  addDialogVisible.value = true
}

function resetAddForm() {
  Object.assign(addForm, defaultAddForm)
  addFormRef.value?.clearValidate()
}

async function handleAddSubmit() {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    await createInventory({ ...addForm })
    ElMessage.success('入库成功')
    addDialogVisible.value = false
    fetchData()
  } catch (e) {}
}

function handleOperation(type, row) {
  opType.value = type
  currentItem.value = row
  if (type === 'scrap') {
    opForm.quantity_change = row.quantity
  } else if (type === 'reserve') {
    opForm.quantity_change = Math.min(1, row.available_quantity)
  } else {
    opForm.quantity_change = 1
  }
  opForm.remark = ''
  if (type === 'open') {
    handleOpen()
  } else {
    opDialogVisible.value = true
  }
}

async function handleOpen() {
  try {
    await openInventory(currentItem.value.id, { remark: opForm.remark })
    ElMessage.success('开封成功')
    fetchData()
  } catch (e) {}
}

async function handleOpSubmit() {
  try {
    const data = {
      inventory_item_id: currentItem.value.id,
      operation_type: opType.value,
      quantity_change: opForm.quantity_change,
      remark: opForm.remark
    }
    if (opType.value === 'outbound') {
      await outboundInventory(currentItem.value.id, data)
    } else if (opType.value === 'return') {
      await returnInventory(currentItem.value.id, data)
    } else if (opType.value === 'scrap') {
      await scrapInventory(currentItem.value.id, data)
    } else if (opType.value === 'check') {
      await inventoryCheck(currentItem.value.id, data)
    } else if (opType.value === 'reserve') {
      await reserveInventory(currentItem.value.id, {
        quantity: opForm.quantity_change,
        remark: opForm.remark
      })
    }
    ElMessage.success('操作成功')
    opDialogVisible.value = false
    fetchData()
  } catch (e) {}
}

function resetOpForm() {
  opForm.quantity_change = 1
  opForm.remark = ''
}

async function viewTimeline(row) {
  try {
    operations.value = await getInventoryOperations(row.id)
    timelineVisible.value = true
  } catch (e) {}
}

onMounted(async () => {
  await fetchMaterials()
  fetchData()
})
</script>

<style scoped>
:deep(.el-table .status-expired) {
  background: #fde2e2 !important;
}
:deep(.el-table .status-near_expiry) {
  background: #fef0f0 !important;
}
.status-warning {
  color: #e6a23c;
  font-weight: bold;
}
</style>
