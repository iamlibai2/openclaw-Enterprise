<template>
  <div class="bindings-page">
    <div class="page-header">
      <h1>绑定配置</h1>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        新建绑定
      </el-button>
    </div>

    <!-- 绑定列表 -->
    <el-card class="bindings-card">
      <template #header>
        <div class="card-header">
          <span>绑定规则列表</span>
          <span class="hint">按顺序匹配，第一条命中的规则生效</span>
        </div>
      </template>

      <div v-if="bindings.length === 0" class="empty-state">
        <el-empty description="暂无绑定规则">
          <el-button type="primary" @click="showCreateDialog">创建第一个绑定</el-button>
        </el-empty>
      </div>

      <div v-else class="binding-list">
        <div
          v-for="(binding, index) in bindings"
          :key="index"
          class="binding-item"
        >
          <div class="binding-index">#{{ index + 1 }}</div>
          <div class="binding-content">
            <div class="binding-agent">
              <span class="label">Agent:</span>
              <span class="value">{{ getAgentName(binding.agentId) }}</span>
              <el-tag size="small" type="info">{{ binding.agentId }}</el-tag>
            </div>
            <div class="binding-match">
              <span class="label">匹配规则:</span>
              <span class="match-desc">{{ formatMatchDesc(binding.match) }}</span>
            </div>
            <div class="binding-detail">
              <code>{{ JSON.stringify(binding.match) }}</code>
            </div>
          </div>
          <div class="binding-actions">
            <el-button link type="primary" @click="showEditDialog(index)">编辑</el-button>
            <el-button link type="danger" @click="confirmDelete(index)">删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 默认 Agent 配置 -->
    <el-card class="default-agent-card">
      <template #header>
        <span>默认 Agent</span>
      </template>
      <div class="default-agent-content">
        <span class="desc">未命中任何绑定规则时，消息将路由到默认 Agent</span>
        <div class="default-agent-select">
          <span class="label">默认 Agent:</span>
          <el-select v-model="defaultAgentId" @change="setDefaultAgent" style="width: 200px">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name || agent.id"
              :value="agent.id"
            />
          </el-select>
        </div>
      </div>
    </el-card>

    <!-- 匹配测试 -->
    <el-card class="test-card">
      <template #header>
        <span>匹配测试</span>
      </template>
      <div class="test-content">
        <div class="test-form">
          <el-form :inline="true">
            <el-form-item label="渠道">
              <el-select v-model="testForm.channel" placeholder="选择渠道" clearable style="width: 150px">
                <el-option
                  v-for="channel in channels"
                  :key="channel.name"
                  :label="channel.displayName"
                  :value="channel.name"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="账号">
              <el-select v-model="testForm.accountId" placeholder="选择账号" clearable style="width: 150px">
                <el-option
                  v-for="account in testAccounts"
                  :key="account.id"
                  :label="account.id"
                  :value="account.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="会话类型">
              <el-select v-model="testForm.peerKind" placeholder="全部" clearable style="width: 120px">
                <el-option label="单聊" value="direct" />
                <el-option label="群聊" value="group" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runTest" :loading="testing">测试</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div v-if="testResult" class="test-result">
          <el-divider content-position="left">测试结果</el-divider>
          <div class="result-content">
            <div class="result-item">
              <span class="result-label">路由到 Agent:</span>
              <el-tag type="success" size="large">{{ testResult.agentName }}</el-tag>
              <span class="result-id">{{ testResult.agentId }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">匹配来源:</span>
              <el-tag :type="testResult.source === 'binding' ? 'primary' : 'info'">
                {{ testResult.source === 'binding' ? '绑定规则' : '默认 Agent' }}
              </el-tag>
            </div>
            <div v-if="testResult.matchedBinding" class="result-item">
              <span class="result-label">命中规则:</span>
              <span>#{{ testResult.matchedIndex + 1 }}</span>
              <code class="result-code">{{ JSON.stringify(testResult.matchedBinding.match) }}</code>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 创建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingIndex !== null ? '编辑绑定' : '新建绑定'"
      width="550px"
    >
      <el-form :model="formData" ref="formRef" label-width="100px" :rules="formRules">
        <el-form-item label="目标 Agent" prop="agentId">
          <el-select v-model="formData.agentId" placeholder="选择 Agent" style="width: 100%">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name || agent.id"
              :value="agent.id"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">匹配规则</el-divider>

        <el-form-item label="渠道">
          <el-select
            v-model="formData.channel"
            placeholder="选择渠道（可选）"
            style="width: 100%"
            clearable
            @change="onChannelChange"
          >
            <el-option
              v-for="channel in channels"
              :key="channel.name"
              :label="channel.displayName || channel.name"
              :value="channel.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="账号" v-if="formData.channel">
          <el-select
            v-model="formData.accountId"
            placeholder="选择账号（可选）"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="account in currentChannelAccounts"
              :key="account.id"
              :label="account.displayName || account.id"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="会话类型">
          <el-select
            v-model="formData.peerKind"
            placeholder="全部类型（可选）"
            style="width: 100%"
            clearable
          >
            <el-option label="单聊" value="direct" />
            <el-option label="群聊" value="group" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingIndex !== null ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="400px">
      <p>确定要删除这条绑定规则吗？</p>
      <p class="delete-hint" v-if="deleteIndex !== null">
        Agent: {{ getAgentName(bindings[deleteIndex]?.agentId) }}
      </p>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="doDelete" :loading="deleting">删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { bindingApi, agentApi, configApi } from '../api'
import type { BindingConfig, BindingMatch, AgentConfig } from '../api'

interface Channel {
  name: string
  displayName: string
  accounts: Account[]
  enabled: boolean
}

interface Account {
  id: string
  displayName: string
  enabled: boolean
}

const bindings = ref<BindingConfig[]>([])
const agents = ref<AgentConfig[]>([])
const channels = ref<Channel[]>([])
const defaultAgentId = ref<string>('')

const loading = ref(false)
const dialogVisible = ref(false)
const editingIndex = ref<number | null>(null)
const submitting = ref(false)
const deleteDialogVisible = ref(false)
const deleteIndex = ref<number | null>(null)
const deleting = ref(false)

const formRef = ref()
const formData = ref({
  agentId: '',
  channel: '',
  accountId: '',
  peerKind: ''
})

const formRules = {
  agentId: [{ required: true, message: '请选择 Agent', trigger: 'change' }]
}

// 当前选中渠道的账号列表
const currentChannelAccounts = computed(() => {
  const channel = channels.value.find(c => c.name === formData.value.channel)
  return channel?.accounts || []
})

// 获取 Agent 名称
function getAgentName(agentId: string): string {
  const agent = agents.value.find(a => a.id === agentId)
  return agent?.name || agentId
}

// 格式化匹配规则描述
function formatMatchDesc(match: BindingMatch): string {
  const parts: string[] = []

  if (match.channel) {
    const channel = channels.value.find(c => c.name === match.channel)
    parts.push(channel?.displayName || match.channel)
  }

  if (match.accountId) {
    parts.push(`/ ${match.accountId}`)
  }

  if (match.peer?.kind) {
    parts.push(match.peer.kind === 'direct' ? '(单聊)' : '(群聊)')
  }

  if (match.peer?.id) {
    parts.push(`[Peer: ${match.peer.id}]`)
  }

  return parts.length > 0 ? parts.join(' ') : '匹配所有'
}

// 加载绑定列表
async function loadBindings() {
  loading.value = true
  try {
    const res = await bindingApi.list()
    if (res.data.success) {
      bindings.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载绑定列表失败')
  } finally {
    loading.value = false
  }
}

// 加载 Agent 列表
async function loadAgents() {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载 Agent 列表失败')
  }
}

// 加载渠道配置
async function loadChannels() {
  try {
    const res = await configApi.get()
    if (res.data.success) {
      const config = res.data.data
      const channelsData: Channel[] = []

      // 解析 channels
      if (config.channels) {
        for (const [name, channelConfig] of Object.entries(config.channels)) {
          const cfg = channelConfig as any
          const accounts: Account[] = []

          // 解析账号
          if (cfg.accounts) {
            for (const [accountId, accountConfig] of Object.entries(cfg.accounts)) {
              if (accountId !== 'default' || Object.keys(cfg.accounts).length === 1) {
                accounts.push({
                  id: accountId,
                  displayName: accountId,
                  enabled: (accountConfig as any).enabled !== false
                })
              }
            }
          }

          channelsData.push({
            name,
            displayName: getChannelDisplayName(name),
            accounts,
            enabled: cfg.enabled !== false
          })
        }
      }

      channels.value = channelsData
    }
  } catch (e: any) {
    ElMessage.error('加载渠道配置失败')
  }
}

// 获取渠道显示名称
function getChannelDisplayName(name: string): string {
  const names: Record<string, string> = {
    'feishu': '飞书',
    'dingtalk-connector': '钉钉连接器',
    'dingtalk': '钉钉',
    'webchat': 'Web Chat'
  }
  return names[name] || name
}

// 加载默认 Agent
async function loadDefaultAgent() {
  try {
    const res = await bindingApi.getDefaultAgent()
    if (res.data.success) {
      defaultAgentId.value = res.data.data.agentId
    }
  } catch (e: any) {
    // 忽略错误，使用默认值
    defaultAgentId.value = 'main'
  }
}

// 设置默认 Agent
async function setDefaultAgent() {
  try {
    const res = await bindingApi.setDefaultAgent(defaultAgentId.value)
    if (res.data.success) {
      ElMessage.success('默认 Agent 已更新')
    } else {
      ElMessage.error(res.data.error || '设置失败')
    }
  } catch (e: any) {
    ElMessage.error('设置默认 Agent 失败')
  }
}

// 渠道变更时清空账号选择
function onChannelChange() {
  formData.value.accountId = ''
}

// 显示创建弹窗
function showCreateDialog() {
  editingIndex.value = null
  formData.value = {
    agentId: '',
    channel: '',
    accountId: '',
    peerKind: ''
  }
  dialogVisible.value = true
}

// 显示编辑弹窗
function showEditDialog(index: number) {
  const binding = bindings.value[index]
  editingIndex.value = index
  formData.value = {
    agentId: binding.agentId,
    channel: binding.match.channel || '',
    accountId: binding.match.accountId || '',
    peerKind: binding.match.peer?.kind || ''
  }
  dialogVisible.value = true
}

// 提交表单
async function submitForm() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    // 构建 match 对象
    const match: BindingMatch = {}
    if (formData.value.channel) {
      match.channel = formData.value.channel
    }
    if (formData.value.accountId) {
      match.accountId = formData.value.accountId
    }
    if (formData.value.peerKind) {
      match.peer = { kind: formData.value.peerKind as 'direct' | 'group' }
    }

    const data: BindingConfig = {
      agentId: formData.value.agentId,
      match
    }

    let res
    if (editingIndex.value !== null) {
      res = await bindingApi.update(editingIndex.value, data)
    } else {
      res = await bindingApi.create(data)
    }

    if (res.data.success) {
      ElMessage.success(editingIndex.value !== null ? '绑定已更新' : '绑定创建成功')
      dialogVisible.value = false
      loadBindings()
    } else {
      ElMessage.error(res.data.error || '操作失败')
    }
  } catch (e: any) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

// 确认删除
function confirmDelete(index: number) {
  deleteIndex.value = index
  deleteDialogVisible.value = true
}

// 执行删除
async function doDelete() {
  if (deleteIndex.value === null) return

  deleting.value = true
  try {
    const res = await bindingApi.delete(deleteIndex.value)
    if (res.data.success) {
      ElMessage.success('绑定已删除')
      deleteDialogVisible.value = false
      loadBindings()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch (e: any) {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = false
  }
}

// ==================== 匹配测试 ====================

const testForm = ref({
  channel: '',
  accountId: '',
  peerKind: ''
})

const testing = ref(false)
const testResult = ref<{
  agentId: string
  agentName: string
  source: 'binding' | 'default'
  matchedBinding?: BindingConfig
  matchedIndex: number
} | null>(null)

// 测试账号列表（根据选中渠道动态变化）
const testAccounts = computed(() => {
  const channel = channels.value.find(c => c.name === testForm.value.channel)
  return channel?.accounts || []
})

// 运行测试
async function runTest() {
  testing.value = true
  testResult.value = null

  try {
    const params: { channel?: string; accountId?: string; peerKind?: 'direct' | 'group' } = {}

    if (testForm.value.channel) params.channel = testForm.value.channel
    if (testForm.value.accountId) params.accountId = testForm.value.accountId
    if (testForm.value.peerKind) params.peerKind = testForm.value.peerKind as 'direct' | 'group'

    const res = await bindingApi.testMatch(params)
    if (res.data.success) {
      testResult.value = res.data.data
    } else {
      ElMessage.error(res.data.error || '测试失败')
    }
  } catch (e: any) {
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

// 监听测试渠道变化，清空账号选择
import { watch } from 'vue'
watch(() => testForm.value.channel, () => {
  testForm.value.accountId = ''
})

onMounted(() => {
  loadAgents()
  loadChannels()
  loadBindings()
  loadDefaultAgent()
})
</script>

<style scoped>
.bindings-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin: 0;
}

.bindings-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .hint {
  font-size: 12px;
  color: #909399;
}

.empty-state {
  padding: 40px 0;
}

.binding-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.binding-item {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  background: #f9fafc;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.binding-index {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  min-width: 40px;
}

.binding-content {
  flex: 1;
  margin-left: 12px;
}

.binding-agent {
  margin-bottom: 8px;
}

.binding-agent .label {
  color: #606266;
  margin-right: 8px;
}

.binding-agent .value {
  font-weight: 500;
  margin-right: 8px;
}

.binding-match {
  margin-bottom: 6px;
}

.binding-match .label {
  color: #606266;
  margin-right: 8px;
}

.binding-match .match-desc {
  color: #303133;
}

.binding-detail code {
  font-size: 12px;
  color: #909399;
  background: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.binding-actions {
  display: flex;
  gap: 8px;
}

.default-agent-card {
  margin-bottom: 20px;
}

.default-agent-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.default-agent-content .desc {
  color: #606266;
}

.default-agent-select .label {
  margin-right: 12px;
  color: #303133;
}

.delete-hint {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

/* 匹配测试面板 */
.test-card {
  margin-bottom: 20px;
}

.test-content {
  padding: 8px 0;
}

.test-form {
  margin-bottom: 16px;
}

.test-result {
  margin-top: 16px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-label {
  color: #606266;
  min-width: 100px;
}

.result-id {
  font-size: 12px;
  color: #909399;
}

.result-code {
  font-size: 12px;
  color: #909399;
  background: #f0f2f5;
  padding: 4px 8px;
  border-radius: 4px;
  margin-left: 8px;
}
</style>