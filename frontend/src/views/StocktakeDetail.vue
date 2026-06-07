<template>
  <div class="page-container">
    <div class="page-header">
      <el-button link @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <h2 class="page-title">盘点任务详情</h2>
      <div class="header-actions" v-if="task">
        <el-button @click="exportDiff">
          <el-icon><Download /></el-icon>导出差异明细
        </el-button>
        <el-button
          v-if="canEdit"
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          <el-icon><Document /></el-icon>暂存
        </el-button>
        <el-button
          v-if="canSubmit"
          type="warning"
          :loading="submitting"
          @click="handleSubmit"
        >
          <el-icon><Promotion /></el-icon>提交复核
        </el-button>
        <el-button
          v-if="canConfirm"
          type="success"
          :loading="confirming"
          @click="handleConfirm"
        >
          <el-icon><Check /></el-icon>确认落账
        </el-button>
        <el-button
          v-if="canClose"
          type="danger"
          @click="handleClose"
        >
          <el-icon><Close /></el-icon>关闭任务
        </el-button>
      </div>
    </div>

    <div v-loading="loading" class="detail-wrapper">
      <template v-if="task">
        <el-card shadow="never" class="info-card">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="任务编号">{{ task.task_no }}</el-descriptions-item>
            <el-descriptions-item label="任务标题">{{ task.title }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStocktakeTaskType(task.status)">
                {{ getStocktakeTaskLabel(task.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="盘点范围">
              <span v-if="task.category_filter">{{ getCategoryLabel(task.category_filter) }}</span>
              <span v-else-if="task.location_filter">{{ task.location_filter }}</span>
              <span v-else-if="task.material_ids_filter">指定物料</span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建人">{{ task.creator?.full_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(task.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="提交人">{{ task.submitter?.full_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ formatDate(task.submitted_at) }}</el-descriptions-item>
            <el-descriptions-item label="确认人">{{ task.confirmer?.full_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="确认时间">{{ formatDate(task.confirmed_at) }}</el-descriptions-item>
            <el-descriptions-item label="关闭人">{{ task.closer?.full_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="关闭时间">{{ formatDate(task.closed_at) }}</el-descriptions-item>
            <el-descriptions-item label="任务描述" :span="3">
              {{ task.description || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" class="items-card">
          <template #header>
            <div class="table-header">
              <span>盘点明细（共 {{ task.items?.length || 0 }} 条）</span>
              <div class="table-stats" v-if="task.items">
                <el-tag type="info" size="small">未录入: {{ countByStatus('not_entered') }}</el-tag>
                <el-tag type="primary" size="small">已暂存: {{ countByStatus('saved') }}</el-tag>
                <el-tag type="warning" size="small">已提交: {{ countByStatus('submitted') }}</el-tag>
                <el-tag type="success" size="small">已确认: {{ countByStatus('confirmed') }}</el-tag>
                <el-tag type="danger" size="small" effect="plain" v-if="hasDiff">
                  存在差异: {{ diffCount }} 条
                </el-tag>
              </div>
            </div>
          </template>

          <el-table
            :data="task.items"
            stripe
            border
            :row-class-name="rowClass"
          >
            <el-table-column label="物料编码" width="100" fixed="left">
              <template #default="{ row }">
                {{ row.inventory_item?.material?.code || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="物料名称" width="140" fixed="left">
              <template #default="{ row }">
                {{ row.inventory_item?.material?.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="批次号" prop="inventory_item.batch_no" width="120" fixed="left" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="getStocktakeItemType(row.status)" size="small" effect="dark">
                  {{ getStocktakeItemLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="快照数量" width="100" align="right" class-name="col-snapshot">
              <template #default="{ row }">
                <strong>{{ row.snapshot_quantity }}</strong>
                <span style="color:#909399;font-size:12px;">
                  {{ row.inventory_item?.material?.unit || '' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="当前实时数量" width="110" align="right" class-name="col-current">
              <template #default="{ row }">
                <strong>{{ row.current_quantity ?? '-' }}</strong>
                <el-tag
                  v-if="row.current_quantity !== row.snapshot_quantity"
                  type="warning"
                  size="small"
                  style="margin-left:4px;"
                >
                  变动
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="实盘数量" width="160" align="right" class-name="col-actual">
              <template #default="{ row }">
                <el-input-number
                  v-if="canEdit"
                  v-model="row.actual_quantity"
                  :min="0"
                  step="1"
                  :controls="false"
                  style="width: 120px;"
                  placeholder="请输入"
                  size="small"
                />
                <template v-else>
                  <strong v-if="row.actual_quantity !== null && row.actual_quantity !== undefined">
                    {{ row.actual_quantity }}
                  </strong>
                  <span v-else style="color:#909399;">-</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="差异值" width="100" align="right" class-name="col-diff">
              <template #default="{ row }">
                <template v-if="row.diff_quantity !== null && row.diff_quantity !== undefined">
                  <span :class="getDiffClass(row.diff_quantity)">
                    {{ row.diff_quantity > 0 ? '+' : '' }}{{ row.diff_quantity }}
                  </span>
                </template>
                <span v-else style="color:#909399;">-</span>
              </template>
            </el-table-column>

            <el-table-column label="快照状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.snapshot_status)" size="small">
                  {{ getStatusLabel(row.snapshot_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.current_status)" size="small">
                  {{ row.current_status ? getStatusLabel(row.current_status) : '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="快照存放位置" prop="snapshot_location" width="120" />
            <el-table-column label="当前存放位置" width="120">
              <template #default="{ row }">
                {{ row.inventory_item?.location || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="快照原始有效期" width="140">
              <template #default="{ row }">
                {{ formatDate(row.snapshot_original_expiry_date) }}
              </template>
            </el-table-column>
            <el-table-column label="快照实际失效日期" width="140">
              <template #default="{ row }">
                {{ formatDate(row.snapshot_actual_expiry_date) }}
              </template>
            </el-table-column>

            <el-table-column label="盘点备注" width="180" fixed="right">
              <template #default="{ row }">
                <el-input
                  v-if="canEdit"
                  v-model="row.remark"
                  placeholder="备注"
                  size="small"
                />
                <template v-else>
                  {{ row.remark || '-' }}
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>
    </div>

    <el-dialog v-model="closeDialogVisible" title="关闭盘点任务" width="450px">
      <el-form label-width="90px">
        <el-form-item label="关闭原因">
          <el-input v-model="closeReason" type="textarea" :rows="3" placeholder="请输入关闭原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="doClose">确认关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import {
  getStocktakeTask,
  saveStocktakeItems,
  submitStocktakeTask,
  confirmStocktakeTask,
  closeStocktakeTask,
  exportStocktakeDiff
} from '@/api/stocktake'
import {
  getStocktakeTaskLabel, getStocktakeTaskType,
  getStocktakeItemLabel, getStocktakeItemType,
  getStatusLabel, getStatusType,
  getCategoryLabel
} from '@/utils/dict'

const route = useRoute()
const userStore = useUserStore()

const taskId = computed(() => route.params.id)
const loading = ref(false)
const task = ref(null)
const saving = ref(false)
const submitting = ref(false)
const confirming = ref(false)

const closeDialogVisible = ref(false)
const closeReason = ref('')

const canEdit = computed(() => {
  if (!task.value) return false
  const roleOk = ['admin', 'manager', 'operator'].includes(userStore.userInfo?.role)
  const statusOk = task.value.status === 'in_progress'
  return roleOk && statusOk
})

const canSubmit = computed(() => {
  if (!task.value) return false
  const roleOk = ['admin', 'manager', 'operator'].includes(userStore.userInfo?.role)
  const statusOk = task.value.status === 'in_progress'
  return roleOk && statusOk
})

const canConfirm = computed(() => {
  if (!task.value) return false
  const roleOk = ['admin', 'manager'].includes(userStore.userInfo?.role)
  const statusOk = task.value.status === 'pending_review'
  return roleOk && statusOk
})

const canClose = computed(() => {
  if (!task.value) return false
  const roleOk = ['admin', 'manager'].includes(userStore.userInfo?.role)
  return roleOk && !['confirmed', 'closed'].includes(task.value.status)
})

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

function countByStatus(status) {
  return task.value?.items?.filter(it => it.status === status).length || 0
}

const diffCount = computed(() => {
  return task.value?.items?.filter(it => {
    return it.actual_quantity !== null && it.actual_quantity !== undefined
      && it.actual_quantity !== it.snapshot_quantity
  }).length || 0
})

const hasDiff = computed(() => diffCount.value > 0)

function getDiffClass(diff) {
  if (diff > 0) return 'status-normal'
  if (diff < 0) return 'status-expired'
  return ''
}

function rowClass({ row }) {
  const hasChange = row.current_quantity !== row.snapshot_quantity
  const hasActualDiff = row.diff_quantity !== null && row.diff_quantity !== undefined && row.diff_quantity !== 0
  if (hasActualDiff) return 'row-has-diff'
  if (hasChange) return 'row-has-change'
  return ''
}

watch(
  () => task.value?.items,
  (items) => {
    if (!items) return
    items.forEach(it => {
      if (it.actual_quantity !== null && it.actual_quantity !== undefined) {
        it.diff_quantity = it.actual_quantity - it.snapshot_quantity
      }
    })
  },
  { deep: true }
)

async function fetchData() {
  loading.value = true
  try {
    task.value = await getStocktakeTask(taskId.value)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!task.value?.items?.length) return
  const item_ids = []
  const items = []
  task.value.items.forEach(it => {
    if (it.actual_quantity !== null && it.actual_quantity !== undefined) {
      item_ids.push(it.id)
      items.push({ actual_quantity: it.actual_quantity, remark: it.remark })
    }
  })
  if (!item_ids.length) {
    ElMessage.warning('请至少填写一条实盘数量')
    return
  }
  saving.value = true
  try {
    await saveStocktakeItems(task.value.id, { item_ids, items })
    ElMessage.success('暂存成功')
    await fetchData()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  try {
    await ElMessageBox.confirm('提交后将进入待复核状态，确定要提交吗？', '提交确认', { type: 'warning' })
  } catch {
    return
  }
  submitting.value = true
  try {
    await submitStocktakeTask(task.value.id)
    ElMessage.success('已提交复核')
    await fetchData()
  } catch (e) {
  } finally {
    submitting.value = false
  }
}

async function handleConfirm() {
  try {
    await ElMessageBox.confirm(
      '确认落账后将按实盘数量更新库存数据并生成操作记录，此操作不可撤销，确定继续吗？',
      '确认落账',
      { type: 'warning' }
    )
  } catch {
    return
  }
  confirming.value = true
  try {
    await confirmStocktakeTask(task.value.id)
    ElMessage.success('盘点结果已确认落账')
    await fetchData()
  } catch (e) {
  } finally {
    confirming.value = false
  }
}

function handleClose() {
  closeReason.value = ''
  closeDialogVisible.value = true
}

async function doClose() {
  try {
    await closeStocktakeTask(task.value.id, { close_reason: closeReason.value })
    ElMessage.success('盘点任务已关闭')
    closeDialogVisible.value = false
    await fetchData()
  } catch (e) {}
}

async function exportDiff() {
  try {
    const blob = await exportStocktakeDiff(task.value.id)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `stocktake_diff_${task.value.task_no}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (e) {}
}

onMounted(fetchData)
</script>

<style scoped>
.detail-wrapper { margin-top: 16px; }
.info-card { margin-bottom: 16px; }
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-stats { display: flex; gap: 8px; }
.col-snapshot { background: #f0f9ff; }
.col-current { background: #fdf6ec; }
.col-actual { background: #f0f9eb; }
.col-diff { background: #fef0f0; }

:deep(.el-table .row-has-change) {
  background: #fdf6ec !important;
}
:deep(.el-table .row-has-diff) {
  background: #fef0f0 !important;
}
.status-normal { color: #67c23a; font-weight: bold; }
.status-expired { color: #f56c6c; font-weight: bold; }
</style>
