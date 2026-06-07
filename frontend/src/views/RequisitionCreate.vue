<template>
  <div class="page-container">
    <div class="page-header">
      <el-button link @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <h2 class="page-title">新建领用申请</h2>
    </div>

    <el-card shadow="never" class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="申请标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入申请标题" maxlength="200" show-word-limit />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="申请说明">
          <el-input v-model="form.apply_remark" type="textarea" :rows="3" placeholder="请输入申请说明（可选）" />
        </el-form-item>

        <el-divider content-position="left">领用明细</el-divider>
        <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px;">
          请选择需要领用的库存批次。只有状态正常、未过期、未报废且有可用数量的库存可以申请领用。
        </el-alert>

        <el-table :data="form.items" border style="margin-bottom: 16px;">
          <el-table-column label="物料名称" width="180">
            <template #default="{ row }">
              {{ getInventoryItem(row.inventory_item_id)?.material?.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="批次号" width="160">
            <template #default="{ row }">
              {{ getInventoryItem(row.inventory_item_id)?.batch_no || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="可用数量" width="120" align="right">
            <template #default="{ row }">
              <span style="font-weight: bold; color: #409eff;">
                {{ getInventoryItem(row.inventory_item_id)?.available_quantity || 0 }}
                {{ getInventoryItem(row.inventory_item_id)?.material?.unit || '' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="申请数量" width="200">
            <template #default="{ row, $index }">
              <el-input-number
                v-model="row.quantity"
                :min="0.01"
                :max="getInventoryItem(row.inventory_item_id)?.available_quantity || 0.01"
                step="1"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="备注">
            <template #default="{ row }">
              <el-input v-model="row.remark" placeholder="备注（可选）" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ $index }">
              <el-button type="danger" link size="small" @click="removeItem($index)">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-form-item>
          <el-button type="primary" @click="showSelectDialog">
            <el-icon><Plus /></el-icon>添加领用明细
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            <el-icon><Check /></el-icon>提交申请
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog
      v-model="selectDialogVisible"
      title="选择库存"
      width="900px"
      @close="resetSelect"
    >
      <div class="filter-bar" style="padding: 0;">
        <el-form :inline="true" :model="selectFilters">
          <el-form-item label="物料">
            <el-select
              v-model="selectFilters.material_id"
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
          <el-form-item label="关键字">
            <el-input
              v-model="selectFilters.keyword"
              placeholder="物料/批次号"
              clearable
              style="width: 200px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchSelectInventory">
              <el-icon><Search /></el-icon>查询
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        ref="selectTableRef"
        :data="selectInventory"
        v-loading="selectLoading"
        @selection-change="handleSelectionChange"
        stripe
        height="400"
      >
        <el-table-column type="selection" width="50" :selectable="isSelectable" />
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
        <el-table-column label="可用数量" width="110" align="right">
          <template #default="{ row }">
            <span style="font-weight: bold; color: #409eff;">
              {{ row.available_quantity }} {{ row.material?.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="实际失效日期" width="150">
          <template #default="{ row }">
            {{ formatDate(row.actual_expiry_date) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :class="`tag-${row.status}`" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="selectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSelect" :disabled="!selectedInventory.length">
          确认添加（已选 {{ selectedInventory.length }} 项）
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { listMaterials } from '@/api/admin'
import { listInventory } from '@/api/inventory'
import { createRequisition } from '@/api/requisitions'
import { STATUS_OPTIONS, getStatusLabel } from '@/utils/dict'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)

const materials = ref([])
const selectInventory = ref([])
const selectLoading = ref(false)
const selectDialogVisible = ref(false)
const selectedInventory = ref([])

const selectFilters = reactive({
  material_id: '',
  keyword: ''
})

const defaultForm = {
  title: '',
  apply_remark: '',
  items: []
}
const form = reactive({ ...defaultForm, items: [] })

const rules = {
  title: [{ required: true, message: '请输入申请标题', trigger: 'blur' }]
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

function getInventoryItem(id) {
  return selectInventory.value.find(x => x.id === id) || null
}

function isSelectable(row) {
  if (row.status === 'scrapped' || row.status === 'expired' || row.status === 'used_up') return false
  if (row.available_quantity <= 0) return false
  if (form.items.some(x => x.inventory_item_id === row.id)) return false
  return true
}

async function fetchMaterials() {
  try {
    materials.value = await listMaterials({ is_active: true })
  } catch (e) {}
}

async function fetchSelectInventory() {
  selectLoading.value = true
  try {
    const params = {}
    if (selectFilters.material_id) params.material_id = selectFilters.material_id
    if (selectFilters.keyword) params.keyword = selectFilters.keyword
    const list = await listInventory(params)
    selectInventory.value = list.filter(x =>
      x.status !== 'scrapped' && x.status !== 'expired' && x.status !== 'used_up' && x.available_quantity > 0
    )
  } catch (e) {
  } finally {
    selectLoading.value = false
  }
}

function showSelectDialog() {
  selectFilters.material_id = ''
  selectFilters.keyword = ''
  selectedInventory.value = []
  selectDialogVisible.value = true
  fetchSelectInventory()
}

function resetSelect() {
  selectedInventory.value = []
}

function handleSelectionChange(rows) {
  selectedInventory.value = rows
}

function confirmSelect() {
  for (const inv of selectedInventory.value) {
    if (form.items.some(x => x.inventory_item_id === inv.id)) continue
    form.items.push({
      inventory_item_id: inv.id,
      quantity: Math.min(1, inv.available_quantity),
      remark: ''
    })
  }
  selectDialogVisible.value = false
  ElMessage.success(`已添加 ${selectedInventory.value.length} 项`)
}

function removeItem(index) {
  form.items.splice(index, 1)
}

async function handleSubmit() {
  if (!form.items.length) {
    ElMessage.warning('请添加至少一项领用明细')
    return
  }
  for (const item of form.items) {
    if (!item.quantity || item.quantity <= 0) {
      ElMessage.warning('申请数量必须大于0')
      return
    }
  }
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createRequisition({
      title: form.title,
      apply_remark: form.apply_remark,
      items: form.items.map(x => ({
        inventory_item_id: x.inventory_item_id,
        quantity: x.quantity,
        remark: x.remark
      }))
    })
    ElMessage.success('申请提交成功')
    router.push('/requisitions')
  } catch (e) {
  } finally {
    submitting.value = false
  }
}

onMounted(fetchMaterials)
</script>

<style scoped>
.form-card { max-width: 1000px; }
.filter-bar { margin-bottom: 12px; }
</style>
