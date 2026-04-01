<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>安全设置</h1>
      <p>权限管理和安全策略配置</p>
    </el-card>

    <el-card class="content-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="权限管理" name="permissions">
          <el-form label-width="120px">
            <el-form-item label="执行权限模式">
              <el-select v-model="execMode" style="width: 200px">
                <el-option label="完全禁止" value="deny" />
                <el-option label="白名单模式" value="allowlist" />
                <el-option label="完全允许" value="full" />
              </el-select>
            </el-form-item>
            <el-form-item label="网络访问">
              <el-switch v-model="networkAccess" />
            </el-form-item>
            <el-form-item label="文件写入">
              <el-switch v-model="fileWrite" />
            </el-form-item>
            <el-form-item label="消息发送">
              <el-switch v-model="messageSend" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="白名单" name="allowlist">
          <el-table :data="allowlist" stripe>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="value" label="值" />
            <el-table-column label="操作" width="80">
              <template #default>
                <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" class="add-btn">添加白名单项</el-button>
        </el-tab-pane>

        <el-tab-pane label="审计日志" name="audit">
          <el-table :data="auditLogs" stripe>
            <el-table-column prop="time" label="时间" width="180" />
            <el-table-column prop="action" label="操作" />
            <el-table-column prop="result" label="结果" width="100">
              <template #default="{ row }">
                <el-tag :type="row.result === 'allowed' ? 'success' : 'danger'">
                  {{ row.result }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('permissions')
const execMode = ref('allowlist')
const networkAccess = ref(true)
const fileWrite = ref(true)
const messageSend = ref(true)

const allowlist = ref([
  { type: '命令', value: 'git status' },
  { type: '命令', value: 'npm install' },
  { type: '路径', value: '~/.openclaw/**' },
])

const auditLogs = ref([
  { time: '2026-03-30 16:40:26', action: 'exec: python script.py', result: 'blocked' },
  { time: '2026-03-30 16:35:12', action: 'exec: git status', result: 'allowed' },
  { time: '2026-03-30 16:30:00', action: 'web_fetch: https://docs.openclaw.ai', result: 'allowed' },
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

.add-btn {
  margin-top: 16px;
}
</style>