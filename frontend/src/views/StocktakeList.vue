<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">盘点任务管理</h2>
      <el-button type="primary" @click="$router.push('/stocktake/create')" v-if="canCreate">
        <el-icon><Plus /></el-icon>创建盘点任务
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="任务状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in STOCKTAKE_TASK_STATUS_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="任务编号/标题"
            clearable
            style="width: 200px"
          />
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
      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column label="任务编号" prop="task_no" width="160" />
        <el-table-column label="任务标题" prop="title" min-width="200" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStocktakeTaskType(row.status)" size="small">
              {{ getStocktakeTaskLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="盘点范围" width="160">
          <template #default="{ row }">
            <span v-if="row.category_filter">{{ getCategoryLabel(row.category_filter) }}</span>
            <span v-else-if="row.location_filter">{{ row.location_filter }}</span>
            <span v-else-if="row.material_ids_filter">指定物料</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建人" width="100">
          <template #default="{ row }">
            {{ row.creator?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="提交人" width="100">
          <template #default="{ row }">
            {{ row.submitter?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="确认人" width="100">
          <template #default="{ row }">
            {{ row.confirmer?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">
              <el-icon><View /></el-icon>详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !tasks.length" description="暂无盘点任务" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { listStocktakeTasks, closeStocktakeTask } from '@/api/stocktake'
import {
  STOCKTAKE_TASK_STATUS_OPTIONS,
  getStocktakeTaskLabel,
  getStocktakeTaskType,
  getCategoryLabel
} from '@/utils/dict'

const router = useRouter()
const userStore = useUserStore()
const canCreate = computed(() => ['admin', 'manager', 'operator'].includes(userStore.userInfo?.role))

const loading = ref(false)
const tasks = ref([])
const filters = reactive({
  status: '',
  keyword: ''
})

const closeDialogVisible = ref(false)
const currentTask = ref(null)
const closeReason = ref('')

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    tasks.value = await listStocktakeTasks(params)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filters.status = ''
  filters.keyword = ''
  fetchData()
}

function viewDetail(row) {
  router.push(`/stocktake/${row.id}`)
}

function handleClose(row) {
  currentTask.value = row
  closeReason.value = ''
  closeDialogVisible.value = true
}

async function doClose() {
  try {
    await closeStocktakeTask(currentTask.value.id, { close_reason: closeReason.value })
    ElMessage.success('盘点任务已关闭')
    closeDialogVisible.value = false
    fetchData()
  } catch (e) {}
}

onMounted(fetchData)
</script>
