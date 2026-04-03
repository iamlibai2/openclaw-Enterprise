<template>
  <div class="channels-page">
    <div class="page-header">
      <h1>Channel 管理</h1>
      <span class="subtitle">管理外部通信 Channel 与账号配置</span>
    </div>

    <!-- 配置向导入口 -->
    <el-card class="wizard-entry-card">
      <div class="wizard-entry">
        <div class="wizard-info">
          <h3>Channel 配置向导</h3>
          <p>通过向导快速配置飞书、钉钉等 Channel</p>
        </div>
        <div class="wizard-buttons">
          <el-button type="primary" @click="showFeishuWizard">
            <el-icon><ChatDotRound /></el-icon>
            配置飞书
          </el-button>
          <el-button type="primary" @click="showDingtalkWizard">
            <el-icon><ChatDotRound /></el-icon>
            配置钉钉
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Channel 列表 -->
    <div class="channel-list" v-loading="loading">
      <el-card v-for="channel in channels" :key="channel.name" class="channel-card">
        <template #header>
          <div class="channel-header">
            <div class="channel-title">
              <span class="channel-icon">{{ getChannelIcon(channel.name) }}</span>
              <span class="channel-name">{{ channel.displayName }}</span>
              <el-tag size="small" type="info">{{ channel.name }}</el-tag>
            </div>
            <div class="channel-status">
              <el-switch
                v-model="channel.enabled"
                @change="toggleChannel(channel)"
                :disabled="!canEdit"
              />
              <span :class="['status-text', channel.enabled ? 'enabled' : 'disabled']">
                {{ channel.enabled ? '已启用' : '已禁用' }}
              </span>
            </div>
          </div>
        </template>

        <!-- 账号列表 -->
        <div class="accounts-section">
          <div class="accounts-header">
            <span class="section-title">账号列表</span>
            <el-button
              type="primary"
              size="small"
              @click="showAddAccountDialog(channel)"
              :disabled="!canEdit"
            >
              <el-icon><Plus /></el-icon>
              添加账号
            </el-button>
          </div>

          <div v-if="channel.accounts.length === 0" class="no-accounts">
            暂无账号配置
          </div>

          <div v-else class="accounts-grid">
            <div
              v-for="account in channel.accounts"
              :key="account.id"
              class="account-card"
            >
              <div class="account-header">
                <span class="account-id">{{ account.id }}</span>
                <div class="account-actions">
                  <el-button link type="primary" size="small" @click="showEditAccountDialog(channel, account)">
                    编辑
                  </el-button>
                  <el-button link type="danger" size="small" @click="confirmDeleteAccount(channel, account)">
                    删除
                  </el-button>
                </div>
              </div>
              <div class="account-config">
                <template v-for="(value, key) in account.config" :key="key">
                  <div class="config-item" v-if="value !== null && value !== undefined">
                    <span class="config-key">{{ key }}</span>
                    <span class="config-value">
                      <template v-if="isSensitiveField(key)">
                        <span class="sensitive-value">{{ maskSensitive(value) }}</span>
                        <el-button
                          link
                          size="small"
                          @click="toggleShowSensitive(account.id, key)"
                        >
                          {{ showSensitive[`${account.id}_${key}`] ? '隐藏' : '显示' }}
                        </el-button>
                      </template>
                      <template v-else>
                        {{ formatValue(value) }}
                      </template>
                    </span>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Channel 配置 -->
        <div class="channel-config-section">
          <el-collapse>
            <el-collapse-item title="高级配置" name="config">
              <div class="config-grid">
                <div class="config-row" v-if="channel.defaultAccount">
                  <span class="label">默认账号:</span>
                  <span class="value">{{ channel.defaultAccount }}</span>
                </div>
                <div class="config-row" v-if="channel.requireMention !== undefined">
                  <span class="label">需要 @提及:</span>
                  <span class="value">{{ channel.requireMention ? '是' : '否' }}</span>
                </div>
                <div class="config-row" v-if="channel.threadSession !== undefined">
                  <span class="label">串会话模式:</span>
                  <span class="value">{{ channel.threadSession ? '是' : '否' }}</span>
                </div>
                <div class="config-row" v-if="channel.sharedMemoryAcrossConversations !== undefined">
                  <span class="label">跨会话共享记忆:</span>
                  <span class="value">{{ channel.sharedMemoryAcrossConversations ? '是' : '否' }}</span>
                </div>
                <div class="config-row" v-if="channel.dmPolicy">
                  <span class="label">单聊策略:</span>
                  <span class="value">{{ channel.dmPolicy }}</span>
                </div>
                <div class="config-row" v-if="channel.groupPolicy">
                  <span class="label">群聊策略:</span>
                  <span class="value">{{ channel.groupPolicy }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-card>
    </div>

    <!-- 添加/编辑账号弹窗 -->
    <el-dialog
      v-model="accountDialogVisible"
      :title="editingAccount ? '编辑账号' : '添加账号'"
      width="550px"
    >
      <el-form :model="accountForm" ref="accountFormRef" label-width="100px" :rules="accountFormRules">
        <el-form-item label="账号标识" prop="accountId" v-if="!editingAccount">
          <el-input v-model="accountForm.accountId" placeholder="请输入账号标识" />
        </el-form-item>
        <el-form-item label="账号标识" v-else>
          <el-input :value="accountForm.accountId" disabled />
        </el-form-item>

        <el-divider content-position="left">账号配置</el-divider>

        <!-- 飞书配置 -->
        <template v-if="currentChannel?.name === 'feishu'">
          <el-form-item label="App ID">
            <el-input v-model="accountForm.config.appId" placeholder="飞书 App ID" />
          </el-form-item>
          <el-form-item label="App Secret">
            <el-input
              v-model="accountForm.config.appSecret"
              type="password"
              placeholder="飞书 App Secret"
              show-password
            />
          </el-form-item>
        </template>

        <!-- 钉钉配置 -->
        <template v-if="currentChannel?.name === 'dingtalk-connector' || currentChannel?.name === 'dingtalk'">
          <el-form-item label="Client ID">
            <el-input v-model="accountForm.config.clientId" placeholder="钉钉 Client ID" />
          </el-form-item>
          <el-form-item label="Client Secret">
            <el-input
              v-model="accountForm.config.clientSecret"
              type="password"
              placeholder="钉钉 Client Secret"
              show-password
            />
          </el-form-item>
          <el-form-item label="Gateway Token">
            <el-input
              v-model="accountForm.config.gatewayToken"
              type="password"
              placeholder="Gateway Token"
              show-password
            />
          </el-form-item>
        </template>

        <!-- 通用配置 -->
        <el-form-item label="启用状态">
          <el-switch v-model="accountForm.config.enabled" />
        </el-form-item>
        <el-form-item label="群消息策略">
          <el-select v-model="accountForm.config.groupPolicy" placeholder="选择策略" clearable>
            <el-option label="开放" value="open" />
            <el-option label="关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="允许的群">
          <el-input
            v-model="accountForm.groupAllowFromStr"
            placeholder="群 ID 列表，逗号分隔，* 表示全部"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAccountForm" :loading="submitting">
          {{ editingAccount ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="400px">
      <p>确定要删除账号 <strong>{{ deletingAccount?.id }}</strong> 吗？</p>
      <p class="hint">Channel: {{ currentChannel?.displayName }}</p>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="doDeleteAccount" :loading="deleting">删除</el-button>
      </template>
    </el-dialog>

    <!-- Channel 配置向导 -->
    <ChannelWizard
      v-model="wizardVisible"
      :channel-type="wizardChannelType"
      @success="loadChannels"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, ChatDotRound } from '@element-plus/icons-vue'
import { channelApi } from '../api'
import type { Channel, ChannelAccount } from '../api'
import ChannelWizard from '../components/ChannelWizard.vue'

const channels = ref<Channel[]>([])
const loading = ref(false)
const canEdit = ref(false)

// 配置向导
const wizardVisible = ref(false)
const wizardChannelType = ref('')

const showFeishuWizard = () => {
  wizardChannelType.value = 'feishu'
  wizardVisible.value = true
}

const showDingtalkWizard = () => {
  wizardChannelType.value = 'dingtalk'
  wizardVisible.value = true
}

// 账号弹窗
const accountDialogVisible = ref(false)
const currentChannel = ref<Channel | null>(null)
const editingAccount = ref<ChannelAccount | null>(null)
const submitting = ref(false)
const accountFormRef = ref()

const accountForm = reactive({
  accountId: '',
  config: {} as Record<string, any>,
  groupAllowFromStr: ''
})

const accountFormRules = {
  accountId: [{ required: true, message: '请输入账号标识', trigger: 'blur' }]
}

// 删除弹窗
const deleteDialogVisible = ref(false)
const deletingAccount = ref<ChannelAccount | null>(null)
const deleting = ref(false)

// 敏感信息显示控制
const showSensitive = ref<Record<string, boolean>>({})

// 敏感字段列表
const sensitiveFields = ['clientSecret', 'appSecret', 'gatewayToken', 'apiKey', 'secret']

function isSensitiveField(key: string): boolean {
  return sensitiveFields.some(f => key.toLowerCase().includes(f.toLowerCase()))
}

function maskSensitive(value: any): string {
  if (typeof value !== 'string') return '****'
  if (value.length <= 8) return '****'
  return value.substring(0, 4) + '****' + value.substring(value.length - 4)
}

function toggleShowSensitive(accountId: string, key: string) {
  const keyName = `${accountId}_${key}`
  showSensitive.value[keyName] = !showSensitive.value[keyName]
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function getChannelIcon(name: string): string {
  const icons: Record<string, string> = {
    'feishu': '📱',
    'dingtalk-connector': '💬',
    'dingtalk': '💬',
    'webchat': '🌐',
    'wechat': '💚'
  }
  return icons[name] || '📡'
}

// 加载 Channel 列表
async function loadChannels() {
  loading.value = true
  try {
    const res = await channelApi.list()
    if (res.data.success) {
      channels.value = res.data.data
      canEdit.value = res.data.permissions?.can_edit || false
    }
  } catch (e: any) {
    ElMessage.error('加载 Channel 列表失败')
  } finally {
    loading.value = false
  }
}

// 切换 Channel 启用状态
async function toggleChannel(channel: Channel) {
  try {
    const res = await channelApi.update(channel.name, { enabled: channel.enabled })
    if (res.data.success) {
      ElMessage.success(channel.enabled ? 'Channel 已启用' : 'Channel 已禁用')
    } else {
      ElMessage.error(res.data.error || '操作失败')
      channel.enabled = !channel.enabled // 恢复原状态
    }
  } catch (e: any) {
    ElMessage.error('操作失败')
    channel.enabled = !channel.enabled
  }
}

// 显示添加账号弹窗
function showAddAccountDialog(channel: Channel) {
  currentChannel.value = channel
  editingAccount.value = null
  accountForm.accountId = ''
  accountForm.config = { enabled: true }
  accountForm.groupAllowFromStr = ''
  accountDialogVisible.value = true
}

// 显示编辑账号弹窗
function showEditAccountDialog(channel: Channel, account: ChannelAccount) {
  currentChannel.value = channel
  editingAccount.value = account
  accountForm.accountId = account.id
  accountForm.config = { ...account.config }
  accountForm.groupAllowFromStr = account.config.groupAllowFrom?.join(', ') || ''
  accountDialogVisible.value = true
}

// 提交账号表单
async function submitAccountForm() {
  if (!currentChannel.value) return

  try {
    await accountFormRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    // 处理群允许列表
    const config = { ...accountForm.config }
    if (accountForm.groupAllowFromStr) {
      config.groupAllowFrom = accountForm.groupAllowFromStr.split(',').map(s => s.trim()).filter(Boolean)
    }

    let res
    if (editingAccount.value) {
      res = await channelApi.updateAccount(
        currentChannel.value.name,
        editingAccount.value.id,
        config
      )
    } else {
      res = await channelApi.createAccount(
        currentChannel.value.name,
        accountForm.accountId,
        config
      )
    }

    if (res.data.success) {
      ElMessage.success(editingAccount.value ? '账号已更新' : '账号已添加')
      accountDialogVisible.value = false
      loadChannels()
    } else {
      ElMessage.error(res.data.error || '操作失败')
    }
  } catch (e: any) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

// 确认删除账号
function confirmDeleteAccount(channel: Channel, account: ChannelAccount) {
  currentChannel.value = channel
  deletingAccount.value = account
  deleteDialogVisible.value = true
}

// 执行删除账号
async function doDeleteAccount() {
  if (!currentChannel.value || !deletingAccount.value) return

  deleting.value = true
  try {
    const res = await channelApi.deleteAccount(
      currentChannel.value.name,
      deletingAccount.value.id
    )
    if (res.data.success) {
      ElMessage.success('账号已删除')
      deleteDialogVisible.value = false
      loadChannels()
    } else {
      ElMessage.error(res.data.error || '删除失败')
    }
  } catch (e: any) {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadChannels()
})
</script>

<style scoped>
.channels-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin: 0 0 8px 0;
}

.page-header .subtitle {
  color: #909399;
  font-size: 14px;
}

.wizard-entry-card {
  margin-bottom: 20px;
}

.wizard-entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wizard-info h3 {
  font-size: 16px;
  margin: 0 0 4px 0;
}

.wizard-info p {
  font-size: 13px;
  color: #909399;
  margin: 0;
}

.wizard-buttons {
  display: flex;
  gap: 12px;
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.channel-card {
  border-radius: 8px;
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.channel-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.channel-icon {
  font-size: 24px;
}

.channel-name {
  font-size: 18px;
  font-weight: 500;
}

.channel-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-text {
  font-size: 13px;
}

.status-text.enabled {
  color: #67c23a;
}

.status-text.disabled {
  color: #909399;
}

.accounts-section {
  margin-top: 16px;
}

.accounts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.no-accounts {
  color: #909399;
  text-align: center;
  padding: 20px;
  background: #f9fafc;
  border-radius: 8px;
}

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.account-card {
  background: #f9fafc;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e4e7ed;
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.account-id {
  font-weight: 500;
  color: #303133;
}

.account-actions {
  display: flex;
  gap: 8px;
}

.account-config {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.config-key {
  color: #606266;
}

.config-value {
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sensitive-value {
  font-family: monospace;
  color: #909399;
}

.channel-config-section {
  margin-top: 16px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.config-row {
  display: flex;
  gap: 8px;
}

.config-row .label {
  color: #606266;
  min-width: 100px;
}

.config-row .value {
  color: #303133;
}

.hint {
  color: #909399;
  font-size: 13px;
}
</style>