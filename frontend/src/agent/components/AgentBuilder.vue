<template>
  <el-dialog
    v-model="visible"
    title="创建 Agent"
    width="650px"
    :close-on-click-modal="false"
    @closed="onClose"
  >
    <!-- 步骤条 -->
    <el-steps :active="currentStep" align-center class="steps-nav">
      <el-step title="选择来源" />
      <el-step title="选择模板" />
      <el-step title="配置身份" />
      <el-step title="配置权限" />
    </el-steps>

    <div class="step-content">
      <!-- Step 0: 选择来源 -->
      <div v-if="currentStep === 0" class="source-step">
        <div class="source-option" :class="{ active: sourceType === 'template' }" @click="sourceType = 'template'">
          <div class="option-icon">📋</div>
          <div class="option-title">从模板创建</div>
          <div class="option-desc">推荐。基于预设模板快速创建</div>
        </div>
        <div class="source-option" :class="{ active: sourceType === 'blank' }" @click="sourceType = 'blank'">
          <div class="option-icon">🆕</div>
          <div class="option-title">从空白创建</div>
          <div class="option-desc">从零开始创建全新 Agent</div>
        </div>
      </div>

      <!-- Step 1: 选择模板 -->
      <div v-if="currentStep === 1" class="template-step">
        <div v-if="loadingTemplates" class="loading-state">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else class="template-grid">
          <div
            v-for="template in templates"
            :key="template.id"
            class="template-card"
            :class="{ active: selectedTemplate === template.id }"
            @click="selectedTemplate = template.id"
          >
            <div class="template-emoji">{{ template.emoji }}</div>
            <div class="template-name">{{ template.name }}</div>
            <div class="template-desc">{{ template.description }}</div>
            <div class="template-tools">
              <el-tag v-for="tool in template.recommendedTools" :key="tool" size="small">
                {{ tool }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: 配置身份 -->
      <div v-if="currentStep === 2" class="identity-step">
        <el-form :model="agentForm" :rules="formRules" ref="formRef" label-width="80px">
          <el-form-item label="名称" prop="name">
            <el-input v-model="agentForm.name" placeholder="Agent 名称" />
          </el-form-item>
          <el-form-item label="ID" prop="id">
            <el-input v-model="agentForm.id" placeholder="唯一标识符，如 my_assistant" />
          </el-form-item>
          <el-form-item label="Emoji">
            <el-input v-model="agentForm.emoji" placeholder="如 🤖" maxlength="4" />
          </el-form-item>
          <el-form-item label="身份描述">
            <el-input v-model="agentForm.creature" placeholder="如 AI 助手" />
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 3: 配置权限 -->
      <div v-if="currentStep === 3" class="permission-step">
        <div class="config-section">
          <h4>工具权限</h4>
          <el-radio-group v-model="agentForm.toolProfile">
            <el-radio-button v-for="p in toolProfiles" :key="p.id" :label="p.id">
              {{ p.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="config-section">
          <h4>技能配置</h4>
          <p class="hint">创建后可在 Skills 页面配置</p>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
        <el-button v-if="currentStep < 3" type="primary" @click="nextStep">下一步</el-button>
        <el-button v-if="currentStep === 3" type="primary" :loading="creating" @click="onCreate">
          创建
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getAgentList, getTemplates, createFromTemplate } from '../api'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'created', agentId: string): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 步骤
const currentStep = ref(0)
const sourceType = ref<'template' | 'blank'>('template')

// 模板
const templates = ref<any[]>([])
const loadingTemplates = ref(false)
const selectedTemplate = ref('')

// 工具 Profiles
const toolProfiles = ref([
  { id: 'minimal', label: 'Minimal' },
  { id: 'messaging', label: 'Messaging' },
  { id: 'coding', label: 'Coding' },
  { id: 'full', label: 'Full' }
])

// 表单
const formRef = ref<FormInstance>()
const agentForm = ref({
  name: '',
  id: '',
  emoji: '🤖',
  creature: 'AI 助手',
  toolProfile: 'messaging'
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  id: [
    { required: true, message: '请输入 ID', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: 'ID 只能包含字母、数字、下划线和横线', trigger: 'blur' }
  ]
}

// 状态
const creating = ref(false)
const existingIds = ref<Set<string>>(new Set())

// 加载模板列表
async function loadTemplates() {
  loadingTemplates.value = true
  try {
    templates.value = await getTemplates()
    if (templates.value.length > 0) {
      selectedTemplate.value = templates.value[0].id
    }
  } catch (e) {
    console.error('Load templates error:', e)
  } finally {
    loadingTemplates.value = false
  }
}

// 加载现有 Agent ID
async function loadExistingIds() {
  try {
    const agents = await getAgentList()
    existingIds.value = new Set(agents.map(a => a.id))
  } catch (e) {
    console.error('Load agents error:', e)
  }
}

// 下一步
async function nextStep() {
  if (currentStep.value === 1 && sourceType.value === 'blank') {
    // 从空白创建，跳过模板选择
    currentStep.value = 2
    return
  }

  if (currentStep.value === 2) {
    // 验证表单
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return

    // 检查 ID 是否已存在
    if (existingIds.value.has(agentForm.value.id)) {
      ElMessage.error(`ID "${agentForm.value.id}" 已存在`)
      return
    }
  }

  currentStep.value++
}

// 上一步
function prevStep() {
  if (currentStep.value === 2 && sourceType.value === 'blank') {
    // 从空白创建，跳过模板选择
    currentStep.value = 0
    return
  }
  currentStep.value--
}

// 创建
async function onCreate() {
  creating.value = true
  try {
    if (sourceType.value === 'template') {
      // 从模板创建
      const result = await createFromTemplate(selectedTemplate.value, {
        name: agentForm.value.name,
        id: agentForm.value.id,
        tools: { profile: agentForm.value.toolProfile, alsoAllow: [] }
      })
      if (result.success) {
        ElMessage.success('创建成功')
        visible.value = false
        emit('created', result.agentId || '')
      } else {
        ElMessage.error(result.message || '创建失败')
      }
    } else {
      // 从空白创建
      // TODO: 实现空白创建逻辑
      ElMessage.info('空白创建功能开发中')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

// 关闭时重置
function onClose() {
  currentStep.value = 0
  sourceType.value = 'template'
  selectedTemplate.value = ''
  agentForm.value = {
    name: '',
    id: '',
    emoji: '🤖',
    creature: 'AI 助手',
    toolProfile: 'messaging'
  }
}

// 监听打开
watch(visible, (val) => {
  if (val) {
    loadTemplates()
    loadExistingIds()
  }
})
</script>

<style scoped>
.steps-nav {
  margin-bottom: 24px;
}

.step-content {
  min-height: 300px;
}

/* Step 0: 选择来源 */
.source-step {
  display: flex;
  gap: 20px;
  justify-content: center;
  padding: 20px;
}

.source-option {
  width: 200px;
  padding: 24px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.source-option:hover {
  border-color: #409eff;
}

.source-option.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.option-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.option-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.option-desc {
  font-size: 13px;
  color: #909399;
}

/* Step 1: 选择模板 */
.template-step {
  padding: 0 10px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.template-card {
  padding: 16px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.template-card:hover {
  border-color: #409eff;
}

.template-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.template-emoji {
  font-size: 32px;
  margin-bottom: 8px;
}

.template-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.template-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.template-tools {
  display: flex;
  gap: 4px;
}

/* Step 2: 配置身份 */
.identity-step {
  padding: 20px 40px;
}

/* Step 3: 配置权限 */
.permission-step {
  padding: 20px;
}

.config-section {
  margin-bottom: 24px;
}

.config-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.hint {
  font-size: 12px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>