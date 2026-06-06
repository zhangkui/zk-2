<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">预警中心</h2>
      <div>
        <el-button type="primary" @click="handleScan">
          <el-icon><Refresh /></el-icon>刷新预警
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="预警类型">
          <el-select v-model="filters.warning_type" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in WARNING_TYPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in WARNING_STATUS_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
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
      <el-table :data="warnings" v-loading="loading" stripe>
        <el-table-column width="70" label="ID" prop="id" />
        <el-table-column width="120" label="类型">
          <template #default="{ row }">
            <el-tag :type="getWarningTypeTag(row.warning_type)" effect="dark">
              {{ getWarningTypeLabel(row.warning_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预警内容" prop="message" min-width="300" />
        <el-table-column width="120" label="物料">
          <template #default="{ row }">
            {{ row.inventory_item?.material?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column width="120" label="批次号">
          <template #default="{ row }">
            {{ row.inventory_item?.batch_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column width="100" label="状态">
          <template #default="{ row }">
            <el-tag :type="getWarningStatusTag(row.status)">
              {{ getWarningStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column width="160" label="创建时间">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column width="120" label="操作" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              type="primary"
              link
              size="small"
              @click="handleHandle(row)"
            >
              处理
            </el-button>
            <el-button type="primary" link size="small" @click="viewInventory(row)">
              查看库存
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="handleDialogVisible" title="处理预警" width="500px">
      <el-form :model="handleForm" label-width="90px">
        <el-form-item label="处理状态">
          <el-select v-model="handleForm.status" style="width: 100%">
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理备注">
          <el-input v-model="handleForm.handled_remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doHandle">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import {
  listWarnings, handleWarning, triggerWarningScan
} from '@/api/monitoring'
import {
  WARNING_TYPE_OPTIONS, WARNING_STATUS_OPTIONS,
  getWarningTypeLabel, getWarningTypeTag,
  getWarningStatusLabel, getWarningStatusTag
} from '@/utils/dict'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const warnings = ref([])
const handleDialogVisible = ref(false)
const currentWarning = ref(null)

const filters = reactive({
  warning_type: route.query.type || '',
  status: ''
})

const handleForm = reactive({
  status: 'acknowledged',
  handled_remark: ''
})

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filters.warning_type) params.warning_type = filters.warning_type
    if (filters.status) params.status = filters.status
    warnings.value = await listWarnings(params)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filters.warning_type = ''
  filters.status = ''
  fetchData()
}

async function handleScan() {
  try {
    await triggerWarningScan()
    ElMessage.success('预警扫描完成')
    fetchData()
  } catch (e) {}
}

function handleHandle(row) {
  currentWarning.value = row
  handleForm.status = 'acknowledged'
  handleForm.handled_remark = ''
  handleDialogVisible.value = true
}

async function doHandle() {
  try {
    await handleWarning(currentWarning.value.id, { ...handleForm })
    ElMessage.success('处理成功')
    handleDialogVisible.value = false
    fetchData()
  } catch (e) {}
}

function viewInventory(row) {
  router.push({ path: '/inventory', query: { id: row.inventory_item_id } })
}

onMounted(fetchData)
</script>
