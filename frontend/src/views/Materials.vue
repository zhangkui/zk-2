<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">物料管理</h2>
      <el-button type="primary" @click="handleAdd" v-if="canEdit">
        <el-icon><Plus /></el-icon>新增物料
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="分类">
          <el-select v-model="filters.category" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="item in CATEGORY_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.is_active" placeholder="全部" clearable style="width: 140px">
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="物料编码/名称"
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
      <el-table :data="materials" v-loading="loading" stripe>
        <el-table-column label="物料编码" prop="code" width="120" />
        <el-table-column label="物料名称" prop="name" width="160" />
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            {{ getCategoryLabel(row.category) }}
          </template>
        </el-table-column>
        <el-table-column label="规格" prop="specification" width="120" />
        <el-table-column label="单位" prop="unit" width="80" />
        <el-table-column label="生产厂家" prop="manufacturer" width="160" />
        <el-table-column label="最低库存" prop="min_stock" width="100" align="right" />
        <el-table-column label="开封有效期(天)" prop="open_validity_days" width="130" align="right">
          <template #default="{ row }">
            {{ row.open_validity_days || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)" v-if="canEdit">
              编辑
            </el-button>
            <el-button type="primary" link size="small" @click="viewInventory(row)">
              查看库存
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="物料编码" prop="code">
              <el-input v-model="form.code" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="物料名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" style="width: 100%">
                <el-option
                  v-for="item in CATEGORY_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规格">
              <el-input v-model="form.specification" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="form.unit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产厂家">
              <el-input v-model="form.manufacturer" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最低库存">
              <el-input-number v-model="form.min_stock" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开封有效天数">
              <el-input-number
                v-model="form.open_validity_days"
                :min="1"
                placeholder="不限制"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { listMaterials, createMaterial, updateMaterial } from '@/api/admin'
import { CATEGORY_OPTIONS, getCategoryLabel } from '@/utils/dict'

const router = useRouter()
const userStore = useUserStore()
const canEdit = computed(() => ['admin', 'manager'].includes(userStore.userInfo?.role))

const loading = ref(false)
const materials = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)

const filters = reactive({
  category: '',
  is_active: '',
  keyword: ''
})

const defaultForm = {
  id: null,
  code: '',
  name: '',
  category: 'reagent',
  specification: '',
  unit: '',
  manufacturer: '',
  min_stock: 0,
  open_validity_days: null,
  description: '',
  is_active: true
}
const form = reactive({ ...defaultForm })

const rules = {
  code: [{ required: true, message: '请输入物料编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }]
}

const dialogTitle = computed(() => form.id ? '编辑物料' : '新增物料')

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filters.category) params.category = filters.category
    if (filters.is_active !== '') params.is_active = filters.is_active
    if (filters.keyword) params.keyword = filters.keyword
    materials.value = await listMaterials(params)
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filters.category = ''
  filters.is_active = ''
  filters.keyword = ''
  fetchData()
}

function resetForm() {
  Object.assign(form, defaultForm)
  formRef.value?.clearValidate()
}

function handleAdd() {
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row) {
  Object.assign(form, row)
  dialogVisible.value = true
}

function viewInventory(row) {
  router.push({ path: '/inventory', query: { material_id: row.id } })
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    const data = { ...form }
    if (!data.open_validity_days) delete data.open_validity_days
    if (form.id) {
      await updateMaterial(form.id, data)
      ElMessage.success('修改成功')
    } else {
      await createMaterial(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {}
}

onMounted(fetchData)
</script>
