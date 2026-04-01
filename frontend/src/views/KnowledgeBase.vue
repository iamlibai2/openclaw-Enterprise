<template>
  <div class="page-container">
    <el-card class="page-header">
      <div class="header-content">
        <div>
          <h1>知识管理</h1>
          <p>管理 Agent 的知识库文件</p>
        </div>
      </div>
    </el-card>

    <!-- 知识库列表 -->
    <el-card class="content-card">
      <el-table :data="knowledgeBases" stripe v-loading="loading">
        <el-table-column prop="agent_name" label="Agent" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.exists ? 'success' : 'info'" size="small">
              {{ row.exists ? '已创建' : '未创建' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_count" label="文件数" width="100" />
        <el-table-column label="总大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.total_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="300">
          <template #default="{ row }">
            <code class="path-code">{{ row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showFiles(row)" :disabled="!row.exists">
              查看文件
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 文件列表对话框 -->
    <el-dialog v-model="filesVisible" :title="`${currentAgent?.agent_name} 知识库文件`" width="700px">
      <div v-if="currentKnowledge" class="files-info">
        <div class="info-item">
          <span class="label">路径:</span>
          <code>{{ currentKnowledge.path }}</code>
        </div>
        <div class="info-item">
          <span class="label">文件数:</span>
          <span>{{ currentKnowledge.files?.length || 0 }}</span>
        </div>
      </div>

      <el-table :data="currentKnowledge?.files || []" stripe max-height="400">
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type || 'file' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="修改时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.modified) }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

interface KnowledgeBase {
  agent_id: string
  agent_name: string
  file_count: number
  total_size: number
  path: string
  exists: boolean
}

interface KnowledgeFile {
  name: string
  size: number
  modified: string
  type: string
}

const loading = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const filesVisible = ref(false)
const currentAgent = ref<KnowledgeBase | null>(null)
const currentKnowledge = ref<{ path: string; files: KnowledgeFile[] } | null>(null)

const getAuthHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('access_token')}`
})

const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/knowledge', { headers: getAuthHeaders() })
    if (res.data.success) {
      knowledgeBases.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

const showFiles = async (kb: KnowledgeBase) => {
  try {
    const res = await axios.get(`/api/knowledge/${kb.agent_id}`, { headers: getAuthHeaders() })
    if (res.data.success) {
      currentAgent.value = kb
      currentKnowledge.value = res.data.data
      filesVisible.value = true
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '加载文件列表失败')
  }
}

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
}

const formatTime = (time: string) => {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.content-card {
  min-height: 400px;
}

.path-code {
  font-family: monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.files-info {
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .label {
  font-weight: 500;
  color: #606266;
}

.info-item code {
  font-family: monospace;
  font-size: 12px;
}
</style>