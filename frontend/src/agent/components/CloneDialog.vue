<template>
  <el-dialog
    v-model="visible"
    title="克隆 Agent"
    width="450px"
    :close-on-click-modal="false"
  >
    <div class="clone-dialog" v-if="agent">
      <div class="source-info">
        <span class="source-label">源 Agent:</span>
        <span class="source-name">{{ agent.name }}</span>
      </div>

      <el-form :model="form" label-width="100px" style="margin-top: 16px">
        <el-form-item label="新名称">
          <el-input v-model="form.name" placeholder="克隆后的名称" />
        </el-form-item>
        <el-form-item label="新 ID">
          <el-input v-model="form.id" placeholder="英文标识，如 xiaomei_2" />
        </el-form-item>
      </el-form>

      <el-divider>克隆内容</el-divider>

      <div class="clone-options">
        <el-checkbox v-model="form.cloneSoul">灵魂 (SOUL.md)</el-checkbox>
        <el-checkbox v-model="form.cloneIdentity">身份 (IDENTITY.md)</el-checkbox>
        <el-checkbox v-model="form.cloneMemory">记忆 (MEMORY.md)</el-checkbox>
        <el-checkbox v-model="form.cloneUser">主人信息 (USER.md)</el-checkbox>
        <el-checkbox v-model="form.cloneSkills">技能配置</el-checkbox>
        <el-checkbox v-model="form.cloneTools">工具权限</el-checkbox>
      </div>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 16px"
      >
        <template #title>
          通常不建议克隆记忆，新 Agent 应该有自己的记忆
        </template>
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleClone" :loading="cloning">
        确认克隆
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { AgentProfile } from '../types'
import { cloneAgent } from '../api'

const props = defineProps<{
  visible: boolean
  agent?: AgentProfile | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'cloned': [newId: string]
}>()

const visible = ref(props.visible)
const cloning = ref(false)

const form = ref({
  name: '',
  id: '',
  cloneSoul: true,
  cloneIdentity: true,
  cloneMemory: false,
  cloneUser: true,
  cloneSkills: true,
  cloneTools: true
})

watch(() => props.visible, (val) => {
  visible.value = val
  if (val && props.agent) {
    form.value = {
      name: props.agent.name + '_副本',
      id: props.agent.id + '_2',
      cloneSoul: true,
      cloneIdentity: true,
      cloneMemory: false,
      cloneUser: true,
      cloneSkills: true,
      cloneTools: true
    }
  }
})

watch(visible, (val) => {
  emit('update:visible', val)
})

async function handleClone() {
  if (!form.value.name || !form.value.id) {
    ElMessage.warning('请填写名称和 ID')
    return
  }

  cloning.value = true
  try {
    const result = await cloneAgent(props.agent!.id, form.value)
    if (result.success) {
      ElMessage.success('克隆成功')
      visible.value = false
      if (result.newId) {
        emit('cloned', result.newId)
      }
    } else {
      ElMessage.error(result.message || '克隆失败')
    }
  } finally {
    cloning.value = false
  }
}
</script>

<style scoped>
.clone-dialog {
  padding: 0 10px;
}

.source-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-label {
  font-size: 13px;
  color: #999;
}

.source-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.clone-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
</style>