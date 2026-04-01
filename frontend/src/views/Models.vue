<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>模型配置</h1>
      <p>查看和配置可用的 AI 模型</p>
    </el-card>

    <el-card class="content-card">
      <el-table :data="models" stripe>
        <el-table-column prop="name" label="模型名称" width="200" />
        <el-table-column prop="provider" label="提供商" width="150" />
        <el-table-column prop="alias" label="别名" width="150" />
        <el-table-column prop="capabilities" label="能力">
          <template #default="{ row }">
            <el-tag v-for="cap in row.capabilities" :key="cap" size="small" class="capability-tag">
              {{ cap }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.available ? 'success' : 'danger'">
              {{ row.available ? '可用' : '不可用' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const models = ref([
  { name: 'bailian/glm-5', provider: '百炼', alias: 'glm-5', capabilities: ['对话', '推理'], available: true },
  { name: 'bailian/qwen3.5-plus', provider: '百炼', alias: 'qwen3.5-plus', capabilities: ['对话', '代码'], available: true },
  { name: 'bailian/qwen3-coder-next', provider: '百炼', alias: 'qwen3-coder', capabilities: ['代码', '推理'], available: true },
  { name: 'bailian/kimi-k2.5', provider: '百炼', alias: 'kimi', capabilities: ['对话', '长文本'], available: true },
  { name: 'openai/gpt-4o', provider: 'OpenAI', alias: '', capabilities: ['对话', '多模态'], available: false },
  { name: 'anthropic/claude-3.5', provider: 'Anthropic', alias: '', capabilities: ['对话', '推理'], available: false },
])
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.content-card {
  min-height: 500px;
}

.capability-tag {
  margin-right: 4px;
}
</style>