<template>
  <el-dialog
    v-model="visible"
    title="导入 Agent"
    width="500px"
    :close-on-click-modal="false"
    @closed="onClose"
  >
    <div class="import-content">
      <!-- 上传区域 -->
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".openclaw-agent"
        :on-change="onFileChange"
        :on-exceed="onExceed"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            仅支持 .openclaw-agent 文件（由导出功能生成）
          </div>
        </template>
      </el-upload>

      <!-- 已选文件 -->
      <div v-if="selectedFile" class="selected-file">
        <el-icon><Document /></el-icon>
        <span class="file-name">{{ selectedFile.name }}</span>
        <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="importing" :disabled="!selectedFile" @click="onImport">
        导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance } from 'element-plus'
import { importAgent } from '../api'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'imported', agentId: string): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const importing = ref(false)

// 文件选择变化
function onFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFile.value = file.raw
  }
}

// 超出限制
function onExceed() {
  ElMessage.warning('只能上传一个文件')
}

// 执行导入
async function onImport() {
  if (!selectedFile.value) return

  importing.value = true
  try {
    const result = await importAgent(selectedFile.value)
    if (result.success) {
      ElMessage.success(`导入成功：${result.agentId}`)
      visible.value = false
      emit('imported', result.agentId || '')
    } else {
      ElMessage.error(result.message || '导入失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

// 格式化文件大小
function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function onClose() {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}
</script>

<style scoped>
.import-content {
  min-height: 200px;
}

.upload-area {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
}

.selected-file {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
}

.file-size {
  font-size: 12px;
  color: #909399;
}
</style>