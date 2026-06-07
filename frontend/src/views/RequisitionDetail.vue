<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <el-button link @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <h2 class="page-title">领用申请详情</h2>
      <div class="header-actions">
        <template v-if="detail && detail.status === 'pending'">
          <el-button v-if="canCancel" @click="handleCancel">
            <el-icon><Close /></el-icon>取消申请
          </el-button>
          <el-button v-if="canApprove" type="danger" @click="showRejectDialog">
            <el-icon><CloseBold /></el-icon>驳回
          </el-button>
          <el-button v-if="canApprove" type="success" @click="showApproveDialog">
            <el-icon><Check /></el-icon>审批通过
          </el-button>
        </template>
      </div>
    </div>

    <el-card shadow="never" v-if="detail" class="detail-card">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="申请单号">
          <span style="font-weight: bold;">{{ detail.requisition_no }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="申请标题">
          {{ detail.title }}
        </el-descriptions-item>
        <el-descriptions-item label="申请状态">
          <el-tag :type="getRequisitionStatusType(detail.status)" size="small">
            {{ getRequisitionStatusLabel(detail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请人">
          {{ detail.applicant?.full_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">
          {{ formatDate(detail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="申请说明">
          {{ detail.apply_remark || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">领用明细</el-divider>

      <el-table :data="detail.items" border stripe>
        <el-table-column label="物料编码" width="120">
          <template #default="{ row }">
            {{ row.material?.code || row.inventory_item?.material?.code || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="物料名称" width="160">
          <template #default="{ row }">
            {{ row.material?.name || row.inventory_item?.material?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="批次号" width="150">
          <template #default="{ row }">
            {{ row.inventory_item?.batch_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="申请数量" width="120" align="right">
          <template #default="{ row }">
            <span style="font-weight: bold; color: #409eff;">
              {{ row.quantity }} {{ row.material?.unit || row.inventory_item?.material?.unit || '' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="实际出库数量" width="130" align="right">
          <template #default="{ row }">
            <span v-if="row.actual_outbound_quantity != null" style="font-weight: bold; color: #67c23a;">
              {{ row.actual_outbound_quantity }} {{ row.material?.unit || row.inventory_item?.material?.unit || '' }}
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="申请时可用数量" width="140" align="right">
          <template #default="{ row }">
            {{ row.inventory_item?.quantity != null ? `${row.inventory_item?.quantity} (可用: ${row.inventory_item?.available_quantity})` : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="备注">
          <template #default="{ row }">
            {{ row.remark || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <el-divider v-if="detail.status !== 'pending'" content-position="left">审批信息</el-divider>

      <el-descriptions v-if="detail.status !== 'pending'" :column="2" border>
        <template v-if="detail.status === 'approved'">
          <el-descriptions-item label="审批人">
            {{ detail.approver?.full_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="审批时间">
            {{ formatDate(detail.approved_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="审批意见" :span="2">
            {{ detail.approve_remark || '-' }}
          </el-descriptions-item>
        </template>
        <template v-else-if="detail.status === 'rejected'">
          <el-descriptions-item label="驳回人">
            {{ detail.rejecter?.full_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="驳回时间">
            {{ formatDate(detail.rejected_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="驳回意见" :span="2">
            {{ detail.reject_remark || '-' }}
          </el-descriptions-item>
        </template>
        <template v-else-if="detail.status === 'cancelled'">
          <el-descriptions-item label="取消人">
            {{ detail.canceller?.full_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="取消时间">
            {{ formatDate(detail.cancelled_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="取消说明" :span="2">
            {{ detail.cancel_remark || '-' }}
          </el-descriptions-item>
        </template>
      </el-descriptions>
    </el-card>

    <el-dialog v-model="approveDialogVisible" title="审批通过" width="450px">
      <el-form :model="approveForm" label-width="90px">
        <el-form-item label="审批意见">
          <el-input v-model="approveForm.approve_remark" type="textarea" :rows="3" placeholder="请输入审批意见（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="success" @click="doApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectDialogVisible" title="驳回申请" width="450px">
      <el-form :model="rejectForm" label-width="90px">
        <el-form-item label="驳回意见">
          <el-input v-model="rejectForm.reject_remark" type="textarea" :rows="3" placeholder="请输入驳回意见（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消申请" width="450px">
      <el-form :model="cancelForm" label-width="90px">
        <el-form-item label="取消说明">
          <el-input v-model="cancelForm.cancel_remark" type="textarea" :rows="3" placeholder="请输入取消说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">取消</el-button>
        <el-button type="warning" @click="doCancel">确认取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { getRequisition, approveRequisition, rejectRequisition, cancelRequisition } from '@/api/requisitions'
import { getRequisitionStatusLabel, getRequisitionStatusType } from '@/utils/dict'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const detail = ref(null)

const canApprove = computed(() =>
  ['admin', 'manager'].includes(userStore.userInfo?.role)
)
const canCancel = computed(() => {
  if (!detail.value) return false
  return (
    detail.value.applicant_id === userStore.userInfo?.id ||
    ['admin', 'manager'].includes(userStore.userInfo?.role)
  )
})

const approveDialogVisible = ref(false)
const approveForm = reactive({ approve_remark: '' })

const rejectDialogVisible = ref(false)
const rejectForm = reactive({ reject_remark: '' })

const cancelDialogVisible = ref(false)
const cancelForm = reactive({ cancel_remark: '' })

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}

async function fetchDetail() {
  loading.value = true
  try {
    detail.value = await getRequisition(route.params.id)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function showApproveDialog() {
  approveForm.approve_remark = ''
  approveDialogVisible.value = true
}

async function doApprove() {
  try {
    await approveRequisition(detail.value.id, { approve_remark: approveForm.approve_remark })
    ElMessage.success('审批通过成功')
    approveDialogVisible.value = false
    fetchDetail()
  } catch (e) {}
}

function showRejectDialog() {
  rejectForm.reject_remark = ''
  rejectDialogVisible.value = true
}

async function doReject() {
  if (!rejectForm.reject_remark?.trim()) {
    ElMessage.warning('请输入驳回意见')
    return
  }
  try {
    await rejectRequisition(detail.value.id, { reject_remark: rejectForm.reject_remark })
    ElMessage.success('驳回成功')
    rejectDialogVisible.value = false
    fetchDetail()
  } catch (e) {}
}

function handleCancel() {
  ElMessageBox.confirm('确定要取消该申请吗？取消后已预占的库存将被释放。', '提示', {
    type: 'warning'
  }).then(() => {
    cancelForm.cancel_remark = ''
    cancelDialogVisible.value = true
  }).catch(() => {})
}

async function doCancel() {
  try {
    await cancelRequisition(detail.value.id, { cancel_remark: cancelForm.cancel_remark })
    ElMessage.success('取消成功')
    cancelDialogVisible.value = false
    fetchDetail()
  } catch (e) {}
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail-card { max-width: 1200px; }
.header-actions { display: flex; gap: 8px; }
</style>
