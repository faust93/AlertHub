<script setup>
import { ElMessage, ElNotification as notify } from 'element-plus'
import { Menu as IconMenu, Message, Setting, Fold } from '@element-plus/icons-vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { menuCollapsed } from '@/utils/sharedState'

const router = useRouter()
const user = localStorage.getItem('user_id')

const handleSelect = (key, keyPath) => {
    console.log(key, keyPath)
}

async function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    ElMessage.success("Logout")
    router.push('/login')
}

async function onUserSettings(user_id) {
  await router.push(`/home/users/${user_id}`)
}
</script>

<template>
  <el-menu mode="horizontal" :ellipsis="false" @select="handleSelect">
    <!-- img style="width: 60px" src="https://img2.imgtp.com/2024/04/05/DMHKG7pg.jpg" alt="Alert Hub" ❰❰ /-->
    <div style="align-self: center; display: flex;">
      <el-text @click="menuCollapsed = !menuCollapsed" style="cursor: pointer;">☰</el-text>
      <h2>AlertHub</h2>
    </div>
    <div class="flex-grow" />
    <el-menu-item index="1">
      <el-dropdown>
        <el-icon style="margin-right: 8px; margin-top: 1px">
          <setting />
        </el-icon>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="onUserSettings(user)">Settings</el-dropdown-item>
            <el-dropdown-item @click="logout">LogOut</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <span>{{ user }}</span>
    </el-menu-item>
  </el-menu>
</template>

<style scoped>
.flex-grow {
    flex-grow: 1;
}
</style>
