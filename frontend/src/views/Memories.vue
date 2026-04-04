<template>
  <div class="memories-page">
    <div class="page-header">
      <h2>记忆管理</h2>
      <p class="desc">管理 Agent 的对话记忆和长期记忆</p>
    </div>

    <div class="coming-soon">
      <el-empty description="功能开发中，敬请期待">
        <el-button type="primary" @click="$router.push('/agents')">
          前往 Agent 配置
        </el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.memories-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.page-header .desc {
  font-size: 14px;
  color: #666;
}

.coming-soon {
  background: #fafafa;
  border-radius: 8px;
  padding: 60px 20px;
  text-align: center;
}
</style>