<template>
  <el-dialog
    v-model="visible"
    title="工具权限配置"
    width="700px"
    :close-on-click-modal="false"
    @closed="onClose"
  >
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else class="tools-config">
      <!-- Profile 选择 -->
      <div class="config-section">
        <h4 class="section-title">工具配置方案</h4>
        <el-radio-group v-model="selectedProfile" class="profile-group">
          <el-radio-button
            v-for="profile in profiles"
            :key="profile.id"
            :label="profile.id"
          >
            {{ profile.label }}
          </el-radio-button>
        </el-radio-group>
        <p class="profile-hint">
          {{ getProfileHint(selectedProfile) }}
        </p>
      </div>

      <!-- 工具分组 -->
      <div class="config-section">
        <h4 class="section-title">额外允许的工具</h4>
        <p class="section-hint">在选定方案基础上，额外允许以下工具</p>

        <el-input
          v-model="searchQuery"
          placeholder="搜索工具..."
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <div class="tools-groups">
          <div
            v-for="group in filteredGroups"
            :key="group.id"
            class="tool-group"
          >
            <div class="group-header">
              <span class="group-icon">{{ getGroupIcon(group.id) }}</span>
              <span class="group-label">{{ group.label }}</span>
              <span class="group-count">{{ group.tools.length }} 个工具</span>
            </div>
            <div class="group-tools">
              <el-checkbox
                v-for="tool in group.tools"
                :key="tool.id"
                :model-value="isToolSelected(tool.id)"
                :disabled="isToolInProfile(tool)"
                @change="toggleTool(tool.id, $event)"
              >
                <div class="tool-item">
                  <span class="tool-name">{{ tool.label }}</span>
                  <span class="tool-desc">{{ tool.description }}</span>
                  <el-tag v-if="isToolInProfile(tool)" size="small" type="info">
                    方案内置
                  </el-tag>
                </div>
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getToolsCatalog, getAgentTools, updateAgentTools } from '../api'

interface Tool {
  id: string
  label: string
  description: string
  source: string
  defaultProfiles: string[]
}

interface ToolGroup {
  id: string
  label: string
  source: string
  tools: Tool[]
}

interface Profile {
  id: string
  label: string
}

const props = defineProps<{
  agentId: string
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const saving = ref(false)
const profiles = ref<Profile[]>([])
const groups = ref<ToolGroup[]>([])
const selectedProfile = ref('default')
const alsoAllow = ref<string[]>([])
const searchQuery = ref('')

// 过滤后的工具分组
const filteredGroups = computed(() => {
  if (!searchQuery.value) return groups.value

  const query = searchQuery.value.toLowerCase()
  return groups.value
    .map(group => ({
      ...group,
      tools: group.tools.filter(tool =>
        tool.label.toLowerCase().includes(query) ||
        tool.description.toLowerCase().includes(query)
      )
    }))
    .filter(group => group.tools.length > 0)
})

// Profile 说明
const profileHints: Record<string, string> = {
  'minimal': '最小权限，仅包含基础工具',
  'coding': '编程模式，包含文件读写、命令执行等开发工具',
  'messaging': '消息模式，适合日常对话和简单任务',
  'full': '完整权限，允许使用所有工具',
  'default': '使用系统默认配置'
}

function getProfileHint(profileId: string): string {
  return profileHints[profileId] || '自定义配置方案'
}

// 分组图标
const groupIcons: Record<string, string> = {
  'fs': '📁',
  'runtime': '⚡',
  'web': '🌐',
  'knowledge': '🧠',
  'agent': '🤖'
}

function getGroupIcon(groupId: string): string {
  return groupIcons[groupId] || '🔧'
}

// 工具是否在当前 Profile 中
function isToolInProfile(tool: Tool): boolean {
  if (selectedProfile.value === 'full') return true
  if (selectedProfile.value === 'default') return false
  return tool.defaultProfiles?.includes(selectedProfile.value) || false
}

// 工具是否被选中
function isToolSelected(toolId: string): boolean {
  return alsoAllow.value.includes(toolId)
}

// 切换工具选中状态
function toggleTool(toolId: string, checked: boolean) {
  if (checked) {
    if (!alsoAllow.value.includes(toolId)) {
      alsoAllow.value.push(toolId)
    }
  } else {
    alsoAllow.value = alsoAllow.value.filter(id => id !== toolId)
  }
}

// 加载工具目录
async function loadCatalog() {
  loading.value = true
  try {
    const result = await getToolsCatalog()
    profiles.value = result.profiles || []
    groups.value = result.groups || []
  } catch (e) {
    ElMessage.error('加载工具目录失败')
  } finally {
    loading.value = false
  }
}

// 加载 Agent 当前配置
async function loadAgentTools() {
  try {
    const result = await getAgentTools(props.agentId)
    selectedProfile.value = result.profile || 'default'
    alsoAllow.value = result.alsoAllow || []
  } catch (e) {
    console.error('Load agent tools error:', e)
  }
}

// 保存配置
async function onSave() {
  saving.value = true
  try {
    await updateAgentTools(props.agentId, {
      profile: selectedProfile.value,
      alsoAllow: alsoAllow.value
    })
    ElMessage.success('保存成功')
    visible.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function onClose() {
  searchQuery.value = ''
}

// 监听对话框打开
watch(visible, (val) => {
  if (val) {
    loadCatalog()
    loadAgentTools()
  }
})
</script>

<style scoped>
.tools-config {
  max-height: 60vh;
  overflow-y: auto;
}

.config-section {
  margin-bottom: 24px;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-hint {
  margin: 0 0 12px 0;
  font-size: 12px;
  color: #909399;
}

.profile-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.profile-hint {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #909399;
}

.search-input {
  margin-bottom: 16px;
}

.tools-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tool-group {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.group-icon {
  font-size: 18px;
}

.group-label {
  font-weight: 500;
  color: #303133;
}

.group-count {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.group-tools {
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tool-name {
  font-size: 13px;
  color: #303133;
}

.tool-desc {
  font-size: 11px;
  color: #909399;
}

:deep(.el-checkbox) {
  align-items: flex-start;
  height: auto;
}

:deep(.el-checkbox__label) {
  white-space: normal;
}
</style>