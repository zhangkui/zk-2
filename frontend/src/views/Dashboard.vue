<template>
  <div class="page-container">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">物料总数</div>
              <div class="stat-value">{{ stats?.total_materials || 0 }}</div>
            </div>
            <div class="stat-icon icon-blue">
              <el-icon size="32"><Box /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" @click="$router.push('/inventory')">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">库存批次</div>
              <div class="stat-value">{{ stats?.total_inventory || 0 }}</div>
            </div>
            <div class="stat-icon icon-green">
              <el-icon size="32"><Goods /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card warning-card" @click="$router.push('/warnings')">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">活动预警</div>
              <div class="stat-value">{{ stats?.total_warnings || 0 }}</div>
            </div>
            <div class="stat-icon icon-orange">
              <el-icon size="32"><Warning /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" @click="$router.push('/operations')">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">今日操作</div>
              <div class="stat-value">{{ stats?.total_operations_today || 0 }}</div>
            </div>
            <div class="stat-icon icon-purple">
              <el-icon size="32"><List /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>效期预警分布</span>
              <el-button size="small" @click="$router.push('/warnings')">查看详情</el-button>
            </div>
          </template>
          <div class="warning-summary">
            <div class="warning-item expired" @click="goWarnings('expired')">
              <div class="warning-icon">
                <el-icon size="24"><CircleClose /></el-icon>
              </div>
              <div>
                <div class="warning-count">{{ stats?.expired_count || 0 }}</div>
                <div class="warning-label">已过期</div>
              </div>
            </div>
            <div class="warning-item near" @click="goWarnings('near_expiry')">
              <div class="warning-icon">
                <el-icon size="24"><Clock /></el-icon>
              </div>
              <div>
                <div class="warning-count">{{ stats?.near_expiry_count || 0 }}</div>
                <div class="warning-label">近效期</div>
              </div>
            </div>
            <div class="warning-item low" @click="goWarnings('low_stock')">
              <div class="warning-icon">
                <el-icon size="24"><Warning /></el-icon>
              </div>
              <div>
                <div class="warning-count">{{ stats?.low_stock_count || 0 }}</div>
                <div class="warning-label">低库存</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>最新预警</span>
          </template>
          <el-table :data="latestWarnings" size="small" :show-header="false">
            <el-table-column width="50" align="center">
              <template #default="{ row }">
                <el-tag :type="getWarningTypeTag(row.warning_type)" size="small" effect="dark">
                  {{ getWarningTypeLabel(row.warning_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column>
              <template #default="{ row }">
                <div class="warning-msg">{{ row.message }}</div>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!latestWarnings.length" description="暂无预警" :image-size="80" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>今日操作记录</span>
          </template>
          <el-table :data="latestOperations" size="small" :show-header="false">
            <el-table-column width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ getOperationTypeLabel(row.operation_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column>
              <template #default="{ row }">
                <div class="op-remark">{{ row.remark || '-' }}</div>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!latestOperations.length" description="暂无操作" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats, listWarnings, listOperations } from '@/api/monitoring'
import {
  getWarningTypeLabel, getWarningTypeTag, getOperationTypeLabel
} from '@/utils/dict'

const router = useRouter()
const stats = ref(null)
const latestWarnings = ref([])
const latestOperations = ref([])

async function fetchData() {
  try {
    stats.value = await getDashboardStats()
  } catch (e) {}
  try {
    const ws = await listWarnings({ status: 'active' })
    latestWarnings.value = ws.slice(0, 5)
  } catch (e) {}
  try {
    const ops = await listOperations({ limit: 5 })
    latestOperations.value = ops
  } catch (e) {}
}

function goWarnings(type) {
  router.push({ path: '/warnings', query: { type } })
}

onMounted(fetchData)
</script>

<style scoped>
.stats-row { margin-bottom: 20px; }

.stat-card { cursor: pointer; transition: transform .2s; }
.stat-card:hover { transform: translateY(-2px); }

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: bold; color: #303133; }

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.icon-blue { background: linear-gradient(135deg, #667eea, #764ba2); }
.icon-green { background: linear-gradient(135deg, #11998e, #38ef7d); }
.icon-orange { background: linear-gradient(135deg, #f093fb, #f5576c); }
.icon-purple { background: linear-gradient(135deg, #4facfe, #00f2fe); }

.warning-card .stat-value { color: #f56c6c; }

.chart-row { margin-bottom: 20px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warning-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .2s;
}
.warning-item:hover { background: #f5f7fa; }

.warning-icon {
  width: 40px; height: 40px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: white;
}
.warning-item.expired .warning-icon { background: #f56c6c; }
.warning-item.near .warning-icon { background: #e6a23c; }
.warning-item.low .warning-icon { background: #409eff; }

.warning-count { font-size: 20px; font-weight: bold; color: #303133; }
.warning-label { font-size: 12px; color: #909399; }

.warning-msg {
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.op-remark { font-size: 13px; color: #606266; }
</style>
