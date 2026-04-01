<template>
  <div class="forbidden-container">
    <div class="forbidden-box">
      <div class="forbidden-icon">
        <el-icon :size="80"><Lock /></el-icon>
      </div>
      <h1>403</h1>
      <p>无权限访问此页面</p>
      <el-button type="primary" @click="goBack">返回上一页</el-button>
      <el-button @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Lock } from '@element-plus/icons-vue'

const router = useRouter()

function goBack() {
  router.back()
}

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.forbidden-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.forbidden-box {
  text-align: center;
  padding: 60px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.forbidden-icon {
  color: #f56c6c;
  margin-bottom: 20px;
}

.forbidden-box h1 {
  font-size: 48px;
  color: #303133;
  margin-bottom: 10px;
}

.forbidden-box p {
  color: #909399;
  margin-bottom: 30px;
}
</style>