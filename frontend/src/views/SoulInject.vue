<template>
  <div class="inject-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1>灵魂注入</h1>
        <p class="page-desc">批量向所有 Agent 的配置文件注入相同内容</p>
      </div>
    </div>

    <!-- 警告提示 -->
    <el-alert
      type="warning"
      title="注意"
      :closable="false"
      style="margin-bottom: 24px"
    >
      <p>此操作将修改所有 Agent 的配置文件，执行前请确认内容无误。</p>
      <p>系统会自动备份原文件（.md.bak），如需恢复请手动处理。</p>
    </el-alert>

    <!-- 注入表单 -->
    <div class="inject-form">
      <!-- 目标文件 -->
      <div class="form-section">
        <h3>目标文件</h3>
        <el-radio-group v-model="form.fileType" class="file-type-group">
          <el-radio-button label="AGENTS">
            <span class="file-option">
              <span class="file-icon">🏠</span>
              <span class="file-name">AGENTS.md</span>
              <span class="file-desc">工作空间配置</span>
            </span>
          </el-radio-button>
          <el-radio-button label="SOUL">
            <span class="file-option">
              <span class="file-icon">💫</span>
              <span class="file-name">SOUL.md</span>
              <span class="file-desc">灵魂配置</span>
            </span>
          </el-radio-button>
          <el-radio-button label="IDENTITY">
            <span class="file-option">
              <span class="file-icon">🎭</span>
              <span class="file-name">IDENTITY.md</span>
              <span class="file-desc">身份配置</span>
            </span>
          </el-radio-button>
          <el-radio-button label="TOOLS">
            <span class="file-option">
              <span class="file-icon">🔧</span>
              <span class="file-name">TOOLS.md</span>
              <span class="file-desc">工具配置</span>
            </span>
          </el-radio-button>
          <el-radio-button label="HEARTBEAT">
            <span class="file-option">
              <span class="file-icon">💓</span>
              <span class="file-name">HEARTBEAT.md</span>
              <span class="file-desc">心跳配置</span>
            </span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 目标 Agent -->
      <div class="form-section">
        <h3>目标 Agent</h3>
        <el-checkbox-group v-model="form.agents" class="agent-checkbox-group">
          <el-checkbox label="">全部 Agent</el-checkbox>
          <el-checkbox
            v-for="agent in agents"
            :key="agent.id"
            :label="agent.id"
          >
            {{ agent.name }} (@{{ agent.id }})
          </el-checkbox>
        </el-checkbox-group>
        <p class="hint">不选择则默认全部 Agent</p>
      </div>

      <!-- 注入方式 -->
      <div class="form-section">
        <h3>注入方式</h3>
        <el-radio-group v-model="form.mode">
          <el-radio label="append">
            <span class="mode-option">
              <b>追加到末尾</b>
              <small>在文件最后添加新内容</small>
            </span>
          </el-radio>
          <el-radio label="prepend">
            <span class="mode-option">
              <b>插入到开头</b>
              <small>在文件开头添加新内容</small>
            </span>
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 注入内容 -->
      <div class="form-section">
        <h3>注入内容</h3>
        <div class="template-quick">
          <span>快速填充：</span>
          <el-button size="small" @click="fillTemplate('venv')">虚拟环境说明</el-button>
          <el-button size="small" @click="fillTemplate('memory')">记忆规范</el-button>
          <el-button size="small" @click="fillTemplate('redlines')">红线规则</el-button>
        </div>
        <textarea
          v-model="form.content"
          class="content-editor"
          placeholder="输入要注入的 Markdown 内容..."
        ></textarea>
        <div class="content-preview" v-if="form.content">
          <div class="preview-header">预览</div>
          <div class="preview-body" v-html="renderedContent"></div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <el-button @click="resetForm">重置</el-button>
        <el-button type="primary" @click="previewInject" :disabled="!form.content">
          <el-icon><View /></el-icon>
          预览影响
        </el-button>
        <el-button type="warning" @click="executeInject" :loading="injecting" :disabled="!form.content">
          <el-icon><MagicStick /></el-icon>
          执行注入
        </el-button>
      </div>
    </div>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewVisible" title="预览影响范围" width="500px">
      <div class="preview-info">
        <p><b>目标文件：</b>{{ form.fileType }}.md</p>
        <p><b>注入方式：</b>{{ form.mode === 'append' ? '追加到末尾' : '插入到开头' }}</p>
        <p><b>目标 Agent：</b>{{ targetCount }} 个</p>
      </div>
      <div class="preview-content">
        <div class="preview-label">即将注入的内容：</div>
        <pre class="preview-code">{{ form.content }}</pre>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="warning" @click="confirmInject" :loading="injecting">
          确认执行
        </el-button>
      </template>
    </el-dialog>

    <!-- 结果对话框 -->
    <el-dialog v-model="resultVisible" title="注入结果" width="500px">
      <div class="result-info">
        <el-result
          :icon="result.success ? 'success' : 'error'"
          :title="result.success ? '注入成功' : '注入失败'"
        >
          <template #extra>
            <div class="result-detail">
              <p>成功注入：<b>{{ result.injected?.length || 0 }}</b> 个 Agent</p>
              <p v-if="result.skipped?.length">跳过：<b>{{ result.skipped.length }}</b> 个</p>
              <div v-if="result.skipped?.length" class="skipped-list">
                <p v-for="s in result.skipped" :key="s.agent">
                  {{ s.agent }}: {{ s.reason }}
                </p>
              </div>
            </div>
          </template>
        </el-result>
      </div>
      <template #footer>
        <el-button type="primary" @click="resultVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { View, MagicStick } from '@element-plus/icons-vue'
import { agentApi, configFileApi, type AgentConfig } from '../api'
import { marked } from 'marked'

interface InjectForm {
  fileType: string
  agents: string[]
  mode: string
  content: string
}

const agents = ref<AgentConfig[]>([])
const form = ref<InjectForm>({
  fileType: 'AGENTS',
  agents: [],
  mode: 'append',
  content: ''
})

const injecting = ref(false)
const previewVisible = ref(false)
const resultVisible = ref(false)
const result = ref<any>({})

const targetCount = computed(() => {
  if (form.value.agents.length === 0) return agents.value.length
  return form.value.agents.length
})

const renderedContent = computed(() => {
  if (!form.value.content) return ''
  return marked(form.value.content)
})

const quickTemplates: Record<string, string> = {
  venv: `## 虚拟环境

**重要**：运行 Python 代码时必须使用虚拟环境：

\`\`\`bash
source /home/iamlibai/workspace/python_env_common/bin/activate
\`\`\`

激活后再执行 Python 命令。`,
  memory: `## 记忆规范

- 每次重要决策必须记录到 memory/ 目录
- 格式：YYYY-MM-DD.md
- 记录内容：决策原因、上下文、结果
- 不要记录敏感信息`,
  redlines: `## 红线规则

**绝对禁止**：
- 泄露用户隐私数据
- 未授权的外部操作
- 执行危险的系统命令（rm -rf 等）
- 向第三方发送用户数据

**必须确认**：
- 发送邮件/消息前确认
- 修改重要配置前确认
- 执行不可逆操作前确认`
}

function fillTemplate(type: string) {
  form.value.content = quickTemplates[type] || ''
}

function resetForm() {
  form.value = {
    fileType: 'AGENTS',
    agents: [],
    mode: 'append',
    content: ''
  }
}

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

function previewInject() {
  if (!form.value.content) {
    ElMessage.warning('请输入注入内容')
    return
  }
  previewVisible.value = true
}

async function executeInject() {
  if (!form.value.content) {
    ElMessage.warning('请输入注入内容')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要向 ${targetCount.value} 个 Agent 的 ${form.value.fileType}.md 注入内容吗？`,
      '确认注入',
      { type: 'warning' }
    )
    previewVisible.value = false
    await doInject()
  } catch {
    // 用户取消
  }
}

async function confirmInject() {
  previewVisible.value = false
  await doInject()
}

async function doInject() {
  injecting.value = true
  try {
    const res = await configFileApi.inject({
      fileType: form.value.fileType,
      content: form.value.content,
      mode: form.value.mode,
      agents: form.value.agents
    })

    if (res.data.success) {
      result.value = {
        success: true,
        injected: res.data.data.injected,
        skipped: res.data.data.skipped
      }
      ElMessage.success(res.data.message)
    } else {
      result.value = { success: false, error: res.data.error }
    }

    resultVisible.value = true
  } catch (e: any) {
    result.value = { success: false, error: e.message }
    resultVisible.value = true
  } finally {
    injecting.value = false
  }
}

onMounted(() => {
  loadAgents()
})
</script>

<style scoped>
.inject-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: #909399;
}

/* 表单 */
.inject-form {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  padding: 24px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

/* 文件类型选择 */
.file-type-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.file-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
}

.file-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.file-desc {
  font-size: 11px;
  color: #909399;
}

/* Agent 选择 */
.agent-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

/* 注入方式 */
.mode-option {
  display: flex;
  flex-direction: column;
}

.mode-option small {
  color: #909399;
}

/* 快速填充 */
.template-quick {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-quick span {
  font-size: 13px;
  color: #606266;
}

/* 内容编辑器 */
.content-editor {
  width: 100%;
  min-height: 200px;
  padding: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
}

.content-editor:focus {
  outline: none;
  border-color: #409eff;
}

/* 内容预览 */
.content-preview {
  margin-top: 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.preview-header {
  padding: 8px 12px;
  background: #f5f7fa;
  font-size: 13px;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
}

.preview-body {
  padding: 16px;
  font-size: 14px;
  line-height: 1.6;
}

/* 操作按钮 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

/* 预览对话框 */
.preview-info {
  margin-bottom: 16px;
}

.preview-info p {
  margin-bottom: 8px;
}

.preview-content {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
}

.preview-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.preview-code {
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

/* 结果 */
.result-detail {
  text-align: left;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 6px;
}

.result-detail p {
  margin-bottom: 8px;
}

.skipped-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  max-height: 150px;
  overflow-y: auto;
}

.skipped-list p {
  font-size: 13px;
  color: #909399;
}
</style>