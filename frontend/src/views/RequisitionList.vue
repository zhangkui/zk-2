<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">领用申请</h2>
      <el-button type="primary" @click="$router.push('/requisitions/create')" v-if="canCreate">
        <el-icon><Plus /></el-icon>新建申请
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="申请状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in REQUISITION_STATUS_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="申请单号/标题"
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
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="申请单号" prop="requisition_no" width="160" />
        <el-table-column label="申请标题" prop="title" min-width="200" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getRequisitionStatusType(row.status)" size="small">
              {{ getRequisitionStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请明细" width="120" align="center">
          <template #default="{ row }">
            {{ row.items?.length || 0 }} 项
          </template>
        </el-table-column>
        <el-table-column label="申请人" width="100">
          <template #default="{ row }">
            {{ row.applicant?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="申请时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="审批人" width="100">
          <template #default="{ row }">
            {{ row.approver?.full_name || row.rejecter?.full_name || row.canceller?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="审批时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.approved_at || row.rejected_at || row.cancelled_at) }}
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
      <el-empty v-if="!loading && !list.length" description="暂无领用申请" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { listRequisitions } from '@/api/requisitions'
import { REQUISITION_STATUS_OPTIONS, getRequisitionStatusLabel, getRequisitionStatusType } from '@/utils/dict'

const router = useRouter()
const userStore = useUserStore()
const canCreate = computed(() => ['admin', 'manager', 'operator'].includes(userStore.userInfo?.role))

const loading = ref(false)
const list = ref([])

const filters = reactive({
  status: '',
  keyword: ''
})

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    list.value = await listRequisitions(params)
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
  router.push(`/requisitions/${row.id}`)
}

onMounted(fetchData)
</script>
