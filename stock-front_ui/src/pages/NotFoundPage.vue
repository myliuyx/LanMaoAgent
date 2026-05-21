<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElButton } from 'element-plus'

const router = useRouter()
</script>

<template>
  <div class="not-found-container">
    <h1>404</h1>
    <p>页面不存在</p>
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<style scoped>
.not-found-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #606266;
}

h1 {
  font-size: 80px;
  color: #409eff;
  margin-bottom: 16px;
}

p {
  font-size: 18px;
  margin-bottom: 24px;
}
</style>
