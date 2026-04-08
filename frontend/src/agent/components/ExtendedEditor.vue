<template>
  <el-dialog
    v-model="visible"
    title="编辑个人资料"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="性别">
        <el-radio-group v-model="form.gender">
          <el-radio label="">未设置</el-radio>
          <el-radio label="男">男</el-radio>
          <el-radio label="女">女</el-radio>
          <el-radio label="其他">其他</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="生日">
        <el-input
          v-model="form.birthday"
          placeholder="格式：MM-DD，如 03-15"
          maxlength="5"
          style="width: 150px"
        />
      </el-form-item>

      <el-form-item label="年龄">
        <el-input
          v-model="form.age_display"
          placeholder="如：20多岁"
          style="width: 150px"
        />
      </el-form-item>

      <el-form-item label="性格">
        <el-input
          v-model="form.personality"
          type="textarea"
          :rows="2"
          placeholder="描述 Agent 的性格特点"
        />
      </el-form-item>

      <el-form-item label="爱好">
        <div class="hobby-input">
          <el-input
            v-model="hobbyInput"
            placeholder="输入爱好后按回车添加"
            @keyup.enter="addHobby"
            style="width: 200px"
          />
          <el-button @click="addHobby" :disabled="!hobbyInput.trim()">添加</el-button>
        </div>
        <div class="hobby-tags" v-if="form.hobbies?.length">
          <el-tag
            v-for="(hobby, index) in form.hobbies"
            :key="index"
            closable
            @close="removeHobby(index)"
            class="hobby-tag"
          >
            {{ hobby }}
          </el-tag>
        </div>
      </el-form-item>

      <el-form-item label="说话风格">
        <el-select v-model="form.voice_style" placeholder="选择说话风格" allow-clear>
          <el-option label="正式" value="正式" />
          <el-option label="亲切" value="亲切" />
          <el-option label="幽默" value="幽默" />
          <el-option label="简洁" value="简洁" />
          <el-option label="温柔" value="温柔" />
          <el-option label="活泼" value="活泼" />
        </el-select>
      </el-form-item>

      <el-form-item label="管理员备注">
        <el-input
          v-model="form.admin_notes"
          type="textarea"
          :rows="2"
          placeholder="仅管理员可见的备注"
        />
      </el-form-item>

      <el-form-item label="标签">
        <div class="tag-input">
          <el-input
            v-model="tagInput"
            placeholder="输入标签后按回车添加"
            @keyup.enter="addTag"
            style="width: 200px"
          />
          <el-button @click="addTag" :disabled="!tagInput.trim()">添加</el-button>
        </div>
        <div class="tag-list" v-if="form.tags?.length">
          <el-tag
            v-for="(tag, index) in form.tags"
            :key="index"
            closable
            @close="removeTag(index)"
            type="info"
            class="tag-item"
          >
            {{ tag }}
          </el-tag>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="save" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { ExtendedProfile } from '../types'
import { updateExtendedProfile } from '../api'

const props = defineProps<{
  modelValue: boolean
  agentId: string
  profile?: ExtendedProfile
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
const hobbyInput = ref('')
const tagInput = ref('')

const form = ref<Partial<ExtendedProfile>>({
  gender: '',
  birthday: '',
  age_display: '',
  personality: '',
  hobbies: [],
  voice_style: '',
  admin_notes: '',
  tags: []
})

// 监听 profile 变化，初始化表单
watch(() => props.profile, (newProfile) => {
  if (newProfile) {
    form.value = {
      gender: newProfile.gender || '',
      birthday: newProfile.birthday || '',
      age_display: newProfile.age_display || '',
      personality: newProfile.personality || '',
      hobbies: newProfile.hobbies || [],
      voice_style: newProfile.voice_style || '',
      admin_notes: newProfile.admin_notes || '',
      tags: newProfile.tags || []
    }
  }
}, { immediate: true })

function addHobby() {
  if (hobbyInput.value.trim()) {
    if (!form.value.hobbies) form.value.hobbies = []
    form.value.hobbies.push(hobbyInput.value.trim())
    hobbyInput.value = ''
  }
}

function removeHobby(index: number) {
  form.value.hobbies?.splice(index, 1)
}

function addTag() {
  if (tagInput.value.trim()) {
    if (!form.value.tags) form.value.tags = []
    form.value.tags.push(tagInput.value.trim())
    tagInput.value = ''
  }
}

function removeTag(index: number) {
  form.value.tags?.splice(index, 1)
}

async function save() {
  saving.value = true
  try {
    const result = await updateExtendedProfile(props.agentId, form.value)
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
.hobby-input,
.tag-input {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.hobby-tags,
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hobby-tag,
.tag-item {
  margin: 0;
}
</style>