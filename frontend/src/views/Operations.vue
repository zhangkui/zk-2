<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">操作记录</h2>
      <el-button type="primary" @click="exportData" plain>
        <el-icon><Download /></el-icon>导出
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="操作类型">
          <el-select v-model="filters.operation_type" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in OPERATION_TYPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
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
      <el-table :data="operations" v-loading="loading" stripe>
        <el-table-column label="ID" prop="id" width="70" />
        <el-table-column label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getOperationTypeLabel(row.operation_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="批次号" width="140">
          <template #default="{ row }">
            {{ row.inventory_item?.batch_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="物料" width="160">
          <template #default="{ row }">
            {{ row.inventory_item?.material?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="数量变化" width="160" align="right">
          <template #default="{ row }">
            <template v-if="row.quantity_change !== 0">
              <span :class="row.quantity_change > 0 ? 'status-normal' : 'status-low_stock'">
                {{ row.quantity_change > 0 ? '+' : '' }}{{ row.quantity_change }}
              </span>
              <span style="color: #909399; margin-left: 8px;">
                ({{ row.quantity_before }} → {{ row.quantity_after }})
              </span>
            </template>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="120">
          <template #default="{ row }">
            {{ row.operator?.full_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.operation_time) }}
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="200">
          <template #default="{ row }">
            {{ row.remark || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { listOperations } from '@/api/monitoring'
import { OPERATION_TYPE_OPTIONS, getOperationTypeLabel } from '@/utils/dict'

const loading = ref(false)
const operations = ref([])
const dateRange = ref([])

const filters = reactive({
  operation_type: '',
  operator_id: ''
})

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}

async function fetchData() {
  loading.value = true
  try {
    const params = { limit: 500 }
    if (filters.operation_type) params.operation_type = filters.operation_type
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    operations.value = await listOperations(params)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filters.operation_type = ''
  dateRange.value = []
  fetchData()
}

function exportData() {
  ElMessage.info('导出功能待实现')
}

onMounted(fetchData)
</script>
