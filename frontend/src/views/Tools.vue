<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>工具配置</h1>
      <p>管理 Agent 可用的工具列表和权限</p>
    </el-card>

    <el-card class="content-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="内置工具" name="builtin">
          <el-table :data="builtinTools" stripe>
            <el-table-column prop="name" label="工具名称" width="180" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'">
                  {{ row.enabled ? '已启用' : '未启用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="自定义工具" name="custom">
          <div class="empty-state">
            <el-empty description="暂无自定义工具">
              <el-button type="primary">添加工具</el-button>
            </el-empty>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('builtin')

const builtinTools = ref([
  { name: 'read', description: '读取文件内容', category: '文件', enabled: true },
  { name: 'write', description: '写入文件内容', category: '文件', enabled: true },
  { name: 'edit', description: '编辑文件', category: '文件', enabled: true },
  { name: 'exec', description: '执行命令', category: '系统', enabled: true },
  { name: 'web_search', description: '搜索网络', category: '网络', enabled: true },
  { name: 'web_fetch', description: '获取网页内容', category: '网络', enabled: true },
  { name: 'browser', description: '浏览器控制', category: '网络', enabled: true },
  { name: 'message', description: '发送消息', category: '通信', enabled: true },
  { name: 'feishu_*', description: '飞书工具集', category: '飞书', enabled: true },
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

.empty-state {
  padding: 40px 0;
}
</style>