<template>
  <el-dialog
    v-model="visible"
    title="编辑身份"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="80px" v-if="form">
      <el-form-item label="名字">
        <el-input v-model="form.name" placeholder="Agent 名字" />
      </el-form-item>
      <el-form-item label="Emoji">
        <el-input v-model="form.emoji" placeholder="如: 🤖" style="width: 100px" />
        <span class="emoji-preview" v-if="form.emoji">{{ form.emoji }}</span>
      </el-form-item>
      <el-form-item label="身份">
        <el-input v-model="form.creature" placeholder="如: 人类女性 AI 助理" />
      </el-form-item>
      <el-form-item label="性格">
        <el-input
          v-model="form.vibe"
          type="textarea"
          :rows="2"
          placeholder="描述 Agent 的性格特征"
        />
      </el-form-item>
      <el-form-item label="头像">
        <el-input v-model="form.avatar" placeholder="头像 URL（可选）" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { IdentityConfig } from '../types'
import { updateAgentIdentity } from '../api'

const props = defineProps<{
  visible: boolean
  identity?: IdentityConfig
  agentId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'saved': []
}>()

const visible = ref(props.visible)
const saving = ref(false)

const form = ref({
  name: '',
  emoji: '',
  creature: '',
  vibe: '',
  avatar: ''
})

// 同步 visible
watch(() => props.visible, (val) => {
  visible.value = val
  if (val && props.identity) {
    form.value = {
      name: props.identity.name || '',
      emoji: props.identity.emoji || '',
      creature: props.identity.creature || '',
      vibe: props.identity.vibe || '',
      avatar: props.identity.avatar || ''
    }
  }
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function handleSave() {
  saving.value = true
  try {
    const success = await updateAgentIdentity(props.agentId, form.value)
    if (success) {
      ElMessage.success('保存成功')
      emit('saved')
      visible.value = false
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.emoji-preview {
  font-size: 24px;
  margin-left: 10px;
}
</style>