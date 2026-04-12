<template>
  <el-dialog
    v-model="visible"
    title="Agent 能力配置"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="capability-editor">
      <!-- 说明 -->
      <div class="editor-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>配置 Agent 的能力标签和专业度评分，用于工作流自动选择 Agent。</span>
      </div>

      <!-- 能力标签 -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">能力标签</span>
          <el-tooltip content="用于匹配工作流节点需求的能力，如'数据分析'、'写作'、'搜索'" placement="top">
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="capability-input">
          <el-select
            v-model="newCapability"
            placeholder="选择或输入能力"
            filterable
            allow-create
            default-first-option
            style="width: 200px"
            @change="addCapability"
          >
            <el-option label="数据分析" value="数据分析" />
            <el-option label="写作" value="写作" />
            <el-option label="搜索" value="搜索" />
            <el-option label="翻译" value="翻译" />
            <el-option label="代码开发" value="代码开发" />
            <el-option label="文档整理" value="文档整理" />
            <el-option label="项目管理" value="项目管理" />
            <el-option label="客户沟通" value="客户沟通" />
          </el-select>
          <el-button @click="addCapability" :disabled="!newCapability">添加</el-button>
        </div>
        <div class="capability-tags" v-if="form.capabilities?.length">
          <el-tag
            v-for="(cap, index) in form.capabilities"
            :key="cap"
            closable
            @close="removeCapability(index)"
            class="capability-tag"
            type="primary"
          >
            {{ cap }}
          </el-tag>
        </div>
      </div>

      <!-- 可执行 Skills -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">可执行 Skills</span>
          <el-tooltip content="Agent 可执行的 Skill 列表，用于工作流节点调用" placement="top">
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="skill-input">
          <el-input
            v-model="newSkill"
            placeholder="输入 Skill ID，如 baidu-search"
            style="width: 200px"
          />
          <el-button @click="addSkill" :disabled="!newSkill.trim()">添加</el-button>
        </div>
        <div class="skill-tags" v-if="form.skills?.length">
          <el-tag
            v-for="(skill, index) in form.skills"
            :key="skill"
            closable
            @close="removeSkill(index)"
            class="skill-tag"
            type="success"
          >
            {{ skill }}
          </el-tag>
        </div>
      </div>

      <!-- 专业度评分 -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">专业度评分</span>
          <el-tooltip content="每项能力的专业度评分 (0-100)，用于 Agent 选择时的优先级计算" placement="top">
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>

        <div class="expertise-list" v-if="form.capabilities?.length">
          <div
            v-for="cap in form.capabilities"
            :key="cap"
            class="expertise-item"
          >
            <span class="expertise-label">{{ cap }}</span>
            <el-slider
              v-model="form.expertiseLevel[cap]"
              :min="0"
              :max="100"
              :step="5"
              show-input
              :show-input-controls="false"
              input-size="small"
              style="flex: 1"
            />
          </div>
        </div>
        <el-empty v-else description="请先添加能力标签" :image-size="40" />
      </div>

      <!-- 状态信息 -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">状态信息</span>
        </div>
        <div class="status-info">
          <div class="status-item">
            <span class="status-label">当前状态</span>
            <el-tag :type="capability?.status === 'idle' ? 'success' : 'warning'" size="small">
              {{ capability?.status === 'idle' ? '空闲' : '繁忙' }}
            </el-tag>
          </div>
          <div class="status-item">
            <span class="status-label">当前任务数</span>
            <span class="status-value">{{ capability?.currentTasks || 0 }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">成功率</span>
            <span class="status-value">{{ ((capability?.successRate || 0.95) * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="save" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, QuestionFilled } from '@element-plus/icons-vue'
import type { AgentCapability } from '../types'
import { getAgentCapability, registerAgentCapability } from '../api'

const props = defineProps<{
  modelValue: boolean
  agentId: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const saving = ref(false)
const loading = ref(false)
const capability = ref<AgentCapability | null>(null)

const newCapability = ref('')
const newSkill = ref('')

const form = reactive({
  capabilities: [] as string[],
  skills: [] as string[],
  expertiseLevel: {} as Record<string, number>
})

// 加载现有能力配置
async function loadCapability() {
  if (!props.agentId) return

  loading.value = true
  try {
    const data = await getAgentCapability(props.agentId)
    capability.value = data

    if (data) {
      form.capabilities = data.capabilities || []
      form.skills = data.skills || []
      form.expertiseLevel = data.expertiseLevel || {}

      // 确保每个能力都有评分
      for (const cap of form.capabilities) {
        if (!form.expertiseLevel[cap]) {
          form.expertiseLevel[cap] = 50
        }
      }
    } else {
      // 初始化默认值
      form.capabilities = []
      form.skills = []
      form.expertiseLevel = {}
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

// 监听对话框打开
watch(visible, (val) => {
  if (val) {
    loadCapability()
    newCapability.value = ''
    newSkill.value = ''
  }
})

// 添加能力
function addCapability() {
  if (newCapability.value && !form.capabilities.includes(newCapability.value)) {
    form.capabilities.push(newCapability.value)
    // 设置默认专业度
    form.expertiseLevel[newCapability.value] = 50
    newCapability.value = ''
  }
}

// 移除能力
function removeCapability(index: number) {
  const cap = form.capabilities[index]
  form.capabilities.splice(index, 1)
  delete form.expertiseLevel[cap]
}

// 添加 Skill
function addSkill() {
  if (newSkill.value.trim() && !form.skills.includes(newSkill.value.trim())) {
    form.skills.push(newSkill.value.trim())
    newSkill.value = ''
  }
}

// 移除 Skill
function removeSkill(index: number) {
  form.skills.splice(index, 1)
}

// 保存
async function save() {
  saving.value = true
  try {
    const result = await registerAgentCapability(props.agentId, {
      capabilities: form.capabilities,
      skills: form.skills,
      expertiseLevel: form.expertiseLevel
    })

    if (result.success) {
      ElMessage.success('保存成功')
      emit('saved')
      visible.value = false
    } else {
      ElMessage.error(result.message || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.capability-editor {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.editor-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #606266;
  font-size: 13px;
}

.section {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.help-icon {
  color: #909399;
  font-size: 14px;
  cursor: help;
}

.capability-input,
.skill-input {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.capability-tags,
.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.capability-tag,
.skill-tag {
  margin: 0;
}

.expertise-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.expertise-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.expertise-label {
  width: 100px;
  font-size: 14px;
  color: #606266;
}

.status-info {
  display: flex;
  gap: 24px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 13px;
  color: #909399;
}

.status-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
</style>