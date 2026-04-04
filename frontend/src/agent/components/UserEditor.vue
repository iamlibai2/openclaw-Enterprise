<template>
  <el-dialog
    v-model="visible"
    title="编辑服务对象"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="80px" v-if="form">
      <el-form-item label="称呼">
        <el-input v-model="form.name" placeholder="如何称呼服务对象" />
      </el-form-item>
      <el-form-item label="代词">
        <el-input v-model="form.pronouns" placeholder="如: 他/她" />
      </el-form-item>
      <el-form-item label="时区">
        <el-select v-model="form.timezone" placeholder="选择时区" style="width: 100%">
          <el-option label="Asia/Shanghai (北京时间)" value="Asia/Shanghai" />
          <el-option label="Asia/Tokyo (东京时间)" value="Asia/Tokyo" />
          <el-option label="America/New_York (纽约时间)" value="America/New_York" />
          <el-option label="Europe/London (伦敦时间)" value="Europe/London" />
          <el-option label="UTC" value="UTC" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.notes" placeholder="简短备注" />
      </el-form-item>
      <el-form-item label="背景">
        <el-input
          v-model="form.context"
          type="textarea"
          :rows="3"
          placeholder="服务对象的背景信息，帮助 Agent 更好地服务"
        />
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
import type { UserConfig } from '../types'
import { updateAgentUser } from '../api'

const props = defineProps<{
  visible: boolean
  user?: UserConfig
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
  pronouns: '',
  timezone: '',
  notes: '',
  context: ''
})

watch(() => props.visible, (val) => {
  visible.value = val
  if (val && props.user) {
    form.value = {
      name: props.user.name || '',
      pronouns: props.user.pronouns || '',
      timezone: props.user.timezone || '',
      notes: props.user.notes || '',
      context: props.user.context || ''
    }
  }
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function handleSave() {
  saving.value = true
  try {
    const success = await updateAgentUser(props.agentId, form.value)
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