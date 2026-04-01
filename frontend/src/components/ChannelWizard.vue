<template>
  <el-dialog
    v-model="visible"
    :title="`${channelInfo?.name || '渠道'}配置向导`"
    width="700px"
    destroy-on-close
    @close="handleClose"
  >
    <el-steps :active="currentStep" align-center class="wizard-steps">
      <el-step title="创建应用" />
      <el-step title="配置权限" />
      <el-step title="配置回调" />
      <el-step title="完成配置" />
    </el-steps>

    <div class="wizard-content">
      <!-- Step 1: 创建应用 -->
      <div v-if="currentStep === 0" class="step-content">
        <div class="step-guide" v-if="channelType === 'feishu'">
          <h3>创建飞书应用</h3>
          <ol class="guide-list">
            <li>
              访问飞书开放平台
              <el-link type="primary" href="https://open.feishu.cn/app" target="_blank">
                打开飞书开放平台 ↗
              </el-link>
            </li>
            <li>点击「创建企业自建应用」</li>
            <li>填写应用名称和描述</li>
            <li>创建完成后，进入应用详情页获取凭证</li>
          </ol>
        </div>

        <div class="step-guide" v-else-if="channelType === 'dingtalk'">
          <h3>创建钉钉应用</h3>
          <ol class="guide-list">
            <li>
              访问钉钉开放平台
              <el-link type="primary" href="https://open.dingtalk.com/develop/orgApp" target="_blank">
                打开钉钉开放平台 ↗
              </el-link>
            </li>
            <li>点击「创建应用」</li>
            <li>选择「H5微应用」或「企业内部应用」</li>
            <li>创建完成后，获取 AppKey 和 AppSecret</li>
          </ol>
        </div>

        <el-form :model="formData" label-width="100px" class="config-form">
          <el-form-item label="App ID" v-if="channelType === 'feishu'" required>
            <el-input v-model="formData.app_id" placeholder="cli_xxxxxxxxxx" />
          </el-form-item>
          <el-form-item label="App Key" v-if="channelType === 'dingtalk'" required>
            <el-input v-model="formData.app_key" placeholder="输入 AppKey" />
          </el-form-item>
          <el-form-item label="App Secret" required>
            <el-input v-model="formData.app_secret" type="password" show-password placeholder="输入 App Secret" />
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 2: 配置权限 -->
      <div v-if="currentStep === 1" class="step-content">
        <div class="step-guide" v-if="channelType === 'feishu'">
          <h3>配置飞书应用权限</h3>
          <ol class="guide-list">
            <li>在应用管理页，进入「权限管理」</li>
            <li>搜索并开通以下权限：
              <ul class="sub-list">
                <li><code>contact:user.base:readonly</code> - 获取用户基本信息</li>
                <li><code>im:message</code> - 获取与发送消息</li>
                <li><code>im:message:send_as_bot</code> - 以应用身份发消息</li>
              </ul>
            </li>
            <li>在「事件订阅」中配置消息接收</li>
          </ol>
        </div>

        <div class="step-guide" v-else-if="channelType === 'dingtalk'">
          <h3>配置钉钉应用权限</h3>
          <ol class="guide-list">
            <li>在应用管理页，进入「权限管理」</li>
            <li>申请以下权限：
              <ul class="sub-list">
                <li>通讯录只读权限</li>
                <li>企业内消息通知权限</li>
                <li>机器人消息推送权限</li>
              </ul>
            </li>
            <li>在「开发管理」中配置服务器出口IP</li>
          </ol>
        </div>

        <el-alert
          title="权限配置提示"
          type="info"
          show-icon
          :closable="false"
          class="permission-tip"
        >
          权限配置需要在开放平台完成，配置后可能需要几分钟生效
        </el-alert>
      </div>

      <!-- Step 3: 配置回调 -->
      <div v-if="currentStep === 2" class="step-content">
        <div class="step-guide" v-if="channelType === 'feishu'">
          <h3>配置飞书事件订阅</h3>
          <ol class="guide-list">
            <li>在「事件订阅」页面，配置请求网址</li>
            <li>添加事件：接收消息 <code>im.message.receive_v1</code></li>
            <li>保存配置并验证</li>
          </ol>
        </div>

        <div class="step-guide" v-else-if="channelType === 'dingtalk'">
          <h3>配置钉钉回调</h3>
          <ol class="guide-list">
            <li>在「开发管理」中配置消息接收地址</li>
            <li>选择「Stream 模式」或「Webhook 模式」</li>
            <li>保存并测试连接</li>
          </ol>
        </div>

        <el-form :model="formData" label-width="100px" class="config-form">
          <el-form-item :label="channelType === 'feishu' ? '事件订阅地址' : '回调地址'">
            <el-input
              v-model="formData.event_url"
              :placeholder="callbackPlaceholder"
            />
            <div class="form-tip">
              填写您的服务器回调地址，OpenClaw 会监听此地址接收消息
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 4: 完成配置 -->
      <div v-if="currentStep === 3" class="step-content">
        <div class="complete-section">
          <el-result
            icon="success"
            title="配置完成"
            sub-title="您的渠道配置已准备就绪"
          />

          <el-form :model="formData" label-width="100px" class="config-form">
            <el-form-item label="机器人名称">
              <el-input v-model="formData.bot_name" placeholder="可选，自定义机器人显示名称" />
            </el-form-item>
            <el-form-item label="启用状态">
              <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="wizard-footer">
        <el-button @click="prevStep" :disabled="currentStep === 0">上一步</el-button>
        <el-button v-if="currentStep < 3" type="primary" @click="nextStep">下一步</el-button>
        <el-button v-else type="primary" @click="submitConfig" :loading="submitting">保存配置</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { channelConfigApi, type ChannelType } from '@/api'

const props = defineProps<{
  modelValue: boolean
  channelType: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const channelTypes = ref<ChannelType[]>([])
const currentStep = ref(0)
const submitting = ref(false)

const formData = ref({
  app_id: '',
  app_key: '',
  app_secret: '',
  event_url: '',
  bot_name: '',
  enabled: true
})

const channelInfo = computed(() => {
  return channelTypes.value.find(t => t.id === props.channelType)
})

const callbackPlaceholder = computed(() => {
  if (props.channelType === 'feishu') {
    return 'https://your-server.com/webhook/feishu'
  } else if (props.channelType === 'dingtalk') {
    return 'https://your-server.com/webhook/dingtalk'
  }
  return 'https://your-server.com/webhook'
})

const loadChannelTypes = async () => {
  try {
    const res = await channelConfigApi.getTypes()
    if (res.data.success) {
      channelTypes.value = res.data.data
    }
  } catch (error) {
    console.error('加载渠道类型失败:', error)
  }
}

const loadExistingConfig = async () => {
  try {
    const res = await channelConfigApi.get(props.channelType)
    if (res.data.success && res.data.data) {
      const config = res.data.data
      formData.value = {
        app_id: config.app_id || '',
        app_key: config.app_key || '',
        app_secret: '',
        event_url: config.event_url || config.callback_url || '',
        bot_name: config.bot_name || '',
        enabled: config.enabled
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const nextStep = () => {
  // 验证当前步骤
  if (currentStep.value === 0) {
    if (props.channelType === 'feishu' && !formData.value.app_id) {
      ElMessage.warning('请输入 App ID')
      return
    }
    if (props.channelType === 'dingtalk' && !formData.value.app_key) {
      ElMessage.warning('请输入 App Key')
      return
    }
    if (!formData.value.app_secret) {
      ElMessage.warning('请输入 App Secret')
      return
    }
  }
  currentStep.value++
}

const prevStep = () => {
  currentStep.value--
}

const submitConfig = async () => {
  submitting.value = true
  try {
    const data: Record<string, any> = {
      enabled: formData.value.enabled
    }

    if (props.channelType === 'feishu') {
      data.app_id = formData.value.app_id
      data.app_secret = formData.value.app_secret
      data.event_url = formData.value.event_url
      data.bot_name = formData.value.bot_name
    } else if (props.channelType === 'dingtalk') {
      data.app_key = formData.value.app_key
      data.app_secret = formData.value.app_secret
      data.callback_url = formData.value.event_url
    }

    const res = await channelConfigApi.save(props.channelType, data)
    if (res.data.success) {
      ElMessage.success('配置保存成功')
      if (res.data.warnings && res.data.warnings.length > 0) {
        ElMessage.warning(res.data.warnings.join(', '))
      }
      emit('success')
      visible.value = false
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '保存失败')
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
  currentStep.value = 0
  formData.value = {
    app_id: '',
    app_key: '',
    app_secret: '',
    event_url: '',
    bot_name: '',
    enabled: true
  }
}

watch(visible, (val) => {
  if (val) {
    loadChannelTypes()
    loadExistingConfig()
  }
})
</script>

<style scoped>
.wizard-steps {
  margin-bottom: 30px;
}

.wizard-content {
  min-height: 300px;
}

.step-content {
  padding: 20px 0;
}

.step-guide h3 {
  font-size: 16px;
  margin-bottom: 16px;
  color: #303133;
}

.guide-list {
  padding-left: 20px;
  line-height: 2;
}

.guide-list li {
  margin-bottom: 8px;
}

.sub-list {
  padding-left: 20px;
  margin-top: 8px;
}

.sub-list li {
  font-size: 13px;
  color: #606266;
}

.sub-list code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.permission-tip {
  margin-top: 20px;
}

.config-form {
  margin-top: 20px;
  max-width: 500px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.complete-section {
  text-align: center;
}

.wizard-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>