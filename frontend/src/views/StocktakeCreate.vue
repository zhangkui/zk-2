<template>
  <div class="page-container">
    <div class="page-header">
      <el-button link @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <h2 class="page-title">创建盘点任务</h2>
    </div>

    <el-card shadow="never" class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入盘点任务标题" maxlength="200" show-word-limit />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="任务描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入任务描述（可选）" />
        </el-form-item>

        <el-divider content-position="left">盘点范围</el-divider>
        <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px;">
          请至少选择一种盘点范围筛选方式。支持按物料分类、存放位置或指定具体物料。
        </el-alert>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="物料分类">
              <el-select v-model="form.category_filter" placeholder="选择分类" clearable style="width: 100%">
                <el-option
                  v-for="item in CATEGORY_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="存放位置">
              <el-input v-model="form.location_filter" placeholder="请输入存放位置" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="指定物料">
              <el-select
                v-model="form.material_ids"
                multiple
                filterable
                placeholder="选择物料（可多选）"
                style="width: 100%"
              >
                <el-option
                  v-for="m in materials"
                  :key="m.id"
                  :label="`${m.code} - ${m.name}`"
                  :value="m.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            <el-icon><Check /></el-icon>创建盘点任务
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listMaterials } from '@/api/admin'
import { createStocktakeTask } from '@/api/stocktake'
import { CATEGORY_OPTIONS } from '@/utils/dict'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)
const materials = ref([])

const defaultForm = {
  title: '',
  description: '',
  category_filter: '',
  location_filter: '',
  material_ids: []
}
const form = reactive({ ...defaultForm })

const rules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }]
}

async function fetchMaterials() {
  try {
    materials.value = await listMaterials({ is_active: true })
  } catch (e) {}
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!form.category_filter && !form.location_filter && (!form.material_ids || form.material_ids.length === 0)) {
    ElMessage.warning('请至少指定一种盘点范围筛选条件')
    return
  }

  submitting.value = true
  try {
    const payload = {
      title: form.title,
      description: form.description || undefined,
      category_filter: form.category_filter || undefined,
      location_filter: form.location_filter || undefined,
      material_ids: form.material_ids && form.material_ids.length ? form.material_ids : undefined
    }
    const task = await createStocktakeTask(payload)
    ElMessage.success('盘点任务创建成功')
    router.replace(`/stocktake/${task.id}`)
  } catch (e) {
  } finally {
    submitting.value = false
  }
}

onMounted(fetchMaterials)
</script>

<style scoped>
.form-card { max-width: 1000px; margin: 0 auto; }
</style>
