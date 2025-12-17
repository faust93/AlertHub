<template>
<div>
  <el-container style="height: 96vh; border: 1px solid #eee;" >
    <div v-if="isMobile" />
    <div v-else>
      <Sidebar></Sidebar>
    </div>
    <el-container>
      <el-header>
        <Header />
      </el-header>
      <el-main style="--el-main-padding: 1px;">
        <router-view></router-view>
      </el-main>
    </el-container>
  </el-container>
</div>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { onMounted } from "vue";
import { useDevice } from '@/utils/useDevice'

const { isMobile } = useDevice()
</script>

<style>
*{
  margin:0;
  padding:0;
  border:0
}
</style>


