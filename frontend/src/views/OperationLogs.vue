<template>
  <div class="operation-logs-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>操作日志</h1>
      <div class="header-actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户/操作"
          style="width: 200px"
          clearable
          @clear="loadLogs"
          @keyup.enter="loadLogs"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="loadLogs"
        />
        <el-button @click="loadLogs">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 日志列表 -->
    <el-table :data="logs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="用户" width="120">
        <template #default="{ row }">
          {{ row.username || '系统' }}
        </template>
      </el-table-column>
      <el-table-column prop="action" label="操作" width="150">
        <template #default="{ row }">
          <el-tag :type="getActionTagType(row.action)" size="small">
            {{ row.action }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource" label="资源" width="120">
        <template #default="{ row }">
          {{ row.resource || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="resource_id" label="资源ID" width="150">
        <template #default="{ row }">
          <span class="resource-id">{{ row.resource_id || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="200">
        <template #default="{ row }">
          <span class="log-details" v-if="row.details">{{ row.details }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP地址" width="130" />
      <el-table-column label="时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLogs"
        @current-change="loadLogs"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import api from '../api'

interface Log {
  id: number
  username?: string
  action: string
  resource: string
  resource_id: string
  details: string
  ip_address: string
  created_at: string
}

const loading = ref(false)
const logs = ref<Log[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const searchKeyword = ref('')
const dateRange = ref<[string, string] | null>(null)

async function loadLogs() {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      limit: pageSize.value
    }

    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }

    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }

    const res = await api.get('/logs/operations', { params })
    if (res.data.success) {
      logs.value = res.data.data || []
      total.value = res.data.total || 0
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function getActionTagType(action: string): string {
  if (action.includes('删除')) return 'danger'
  if (action.includes('创建') || action.includes('添加')) return 'success'
  if (action.includes('修改') || action.includes('更新')) return 'warning'
  return 'info'
}

function formatTime(time: string): string {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.operation-logs-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.resource-id {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.log-details {
  font-size: 13px;
  color: #606266;
}

.text-muted {
  color: #c0c4cc;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>