<template>
  <el-container class="main-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon size="28" color="#409eff"><Box /></el-icon>
        <span>效期追踪系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1f2d3d"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <el-menu-item :index="`/${route.path}`">
            <el-icon><component :is="route.meta.icon" /></el-icon>
            <span>{{ route.meta.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-tag type="success" effect="plain" size="large">
            {{ route.meta.title || '首页' }}
          </el-tag>
        </div>
        <div class="header-right">
          <el-badge :value="warningCount" :hidden="warningCount === 0" class="warning-badge">
            <el-button link @click="$router.push('/warnings')">
              <el-icon size="20"><Warning /></el-icon>
              预警
            </el-button>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" style="background: #409eff">
                {{ userStore.userInfo?.full_name?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="username">{{ userStore.userInfo?.full_name }}</span>
              <el-icon><CaretBottom /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">
                  <el-icon><Key /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>

    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px">
      <el-form :model="pwdForm" label-width="90px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doChangePassword">确认</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { listWarnings } from '@/api/monitoring'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const warningCount = ref(0)
const pwdDialogVisible = ref(false)
const pwdForm = ref({ old_password: '', new_password: '' })

const menuRoutes = computed(() => {
  const children = router.options.routes.find(r => r.path === '/')?.children || []
  return children.filter(r => {
    if (r.meta?.roles && userStore.userInfo) {
      if (!r.meta.roles.includes(userStore.userInfo.role) && userStore.userInfo.role !== 'admin') {
        return false
      }
    }
    return true
  })
})

async function fetchWarningCount() {
  try {
    const list = await listWarnings({ status: 'active' })
    warningCount.value = list.length
  } catch (e) {}
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning'
    }).then(() => {
      userStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    }).catch(() => {})
  } else if (cmd === 'password') {
    pwdDialogVisible.value = true
    pwdForm.value = { old_password: '', new_password: '' }
  }
}

async function doChangePassword() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    ElMessage.warning('请填写完整')
    return
  }
  if (pwdForm.value.new_password.length < 6) {
    ElMessage.warning('新密码长度至少6位')
    return
  }
  try {
    await userStore.changePassword(pwdForm.value.old_password, pwdForm.value.new_password)
    ElMessage.success('密码修改成功')
    pwdDialogVisible.value = false
  } catch (e) {}
}

onMounted(fetchWarningCount)
</script>

<style scoped>
.main-layout { height: 100vh; }

.sidebar {
  background: #1f2d3d;
  color: #fff;
  overflow-y: auto;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid #2d3e53;
}

.sidebar .el-menu { border-right: none; }

.header {
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.warning-badge { margin-right: 10px; }

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username { font-size: 14px; color: #303133; }

.main-content {
  background: #f5f7fa;
  padding: 0;
  overflow-y: auto;
}
</style>
