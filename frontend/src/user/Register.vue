<template>
  <div class="register-page">
    <!-- 星空粒子背景 -->
    <div class="starfield">
      <div v-for="n in 50" :key="n" class="star" :style="getStarStyle(n)"></div>
    </div>

    <!-- 渐变光晕背景 -->
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>

    <!-- 主容器：左右分栏 -->
    <div class="main-container">
      <!-- 左侧：品牌宣传 -->
      <div class="brand-section">
        <div class="brand-content">
          <!-- Logo -->
          <div class="logo-mark">
            <svg viewBox="0 0 40 40" fill="none">
              <path d="M20 4L4 12L20 20L36 12L20 4Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M4 20L20 28L36 20" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M4 28L20 36L36 28" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1 class="brand-name">OpenClaw</h1>
          <p class="brand-tagline">企业级 AI Agent 管理平台</p>

          <!-- 特性四宫格 -->
          <div class="features">
            <div class="feature-item" v-for="(feature, idx) in features" :key="idx">
              <div class="feature-icon" v-html="feature.icon"></div>
              <div class="feature-text">
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.desc }}</p>
              </div>
            </div>
          </div>

          <!-- 底部统计 -->
          <div class="brand-footer">
            <div class="stats">
              <div class="stat-item">
                <span class="stat-value">10+</span>
                <span class="stat-label">消息渠道</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">∞</span>
                <span class="stat-label">Agent</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">99.9%</span>
                <span class="stat-label">可用性</span>
              </div>
            </div>
            <p class="copyright">© 2026 OpenClaw</p>
          </div>
        </div>
      </div>

      <!-- 右侧：注册卡片 -->
      <div class="register-section">
        <div class="register-card" :class="{ focused: isFocused }">
          <!-- 光晕边框 -->
          <div class="card-glow"></div>

          <!-- 注册表单 -->
          <form class="form" @submit.prevent="handleRegister">
            <div class="form-header">
              <h2>员工注册</h2>
              <p>创建您的账户以使用 AI 助手</p>
            </div>

            <!-- 姓名输入 -->
            <div class="field" :class="{ active: focusedField === 'name', filled: form.name }">
              <label>姓名</label>
              <div class="input-wrap">
                <input
                  v-model="form.name"
                  type="text"
                  autocomplete="name"
                  placeholder="请输入真实姓名"
                  @focus="focusedField = 'name'"
                  @blur="focusedField = ''"
                />
                <div class="input-glow"></div>
              </div>
            </div>

            <!-- 邮箱输入 -->
            <div class="field" :class="{ active: focusedField === 'email', filled: form.email }">
              <label>邮箱</label>
              <div class="input-wrap">
                <input
                  v-model="form.email"
                  type="email"
                  autocomplete="email"
                  placeholder="请输入工作邮箱"
                  @focus="focusedField = 'email'"
                  @blur="focusedField = ''"
                />
                <div class="input-glow"></div>
              </div>
            </div>

            <!-- 密码输入 -->
            <div class="field" :class="{ active: focusedField === 'password', filled: form.password }">
              <label>密码</label>
              <div class="input-wrap">
                <input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="至少6个字符"
                  @focus="focusedField = 'password'"
                  @blur="focusedField = ''"
                />
                <button type="button" class="toggle-pw" @click="showPassword = !showPassword">
                  <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                </button>
                <div class="input-glow"></div>
              </div>
            </div>

            <!-- 确认密码输入 -->
            <div class="field" :class="{ active: focusedField === 'confirmPassword', filled: form.confirmPassword }">
              <label>确认密码</label>
              <div class="input-wrap">
                <input
                  v-model="form.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="再次输入密码"
                  @focus="focusedField = 'confirmPassword'"
                  @blur="focusedField = ''"
                />
                <button type="button" class="toggle-pw" @click="showConfirmPassword = !showConfirmPassword">
                  <svg v-if="!showConfirmPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                </button>
                <div class="input-glow"></div>
              </div>
              <p class="field-hint" v-if="form.confirmPassword && form.confirmPassword !== form.password">
                密码不一致
              </p>
            </div>

            <!-- 手机号输入（选填） -->
            <div class="field optional" :class="{ active: focusedField === 'phone', filled: form.phone }">
              <label>手机号 <span class="optional-tag">选填</span></label>
              <div class="input-wrap">
                <input
                  v-model="form.phone"
                  type="tel"
                  autocomplete="tel"
                  placeholder="用于飞书账号自动绑定"
                  @focus="focusedField = 'phone'"
                  @blur="focusedField = ''"
                />
                <div class="input-glow"></div>
              </div>
            </div>

            <!-- 注册按钮 -->
            <button type="submit" class="submit-btn" :disabled="loading" :class="{ loading }">
              <span class="btn-text">{{ loading ? '注册中' : '注册' }}</span>
              <span class="btn-loader" v-if="loading"></span>
              <span class="btn-glow"></span>
              <span class="ripple" v-if="ripple" :style="rippleStyle"></span>
            </button>
          </form>

          <!-- 底部链接 -->
          <div class="form-footer">
            <span>已有账号？</span>
            <a href="#" @click.prevent="router.push('/login')">立即登录</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from './api'
import { useUserStore } from './stores'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  phone: ''
})
const loading = ref(false)
const focusedField = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const ripple = ref(false)
const rippleStyle = ref({})

const isFocused = computed(() => focusedField.value !== '')

const features = [
  {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
    title: '专属 Agent',
    desc: '绑定您的专属 AI 助手'
  },
  {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
    title: '智能对话',
    desc: '多渠道无缝沟通'
  },
  {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
    title: '安全可靠',
    desc: '企业级数据保护'
  },
  {
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
    title: '记忆功能',
    desc: 'AI 记住您的工作偏好'
  }
]

function getStarStyle(n: number) {
  const size = Math.random() * 2 + 1
  return {
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${Math.random() * 3}s`,
    animationDuration: `${2 + Math.random() * 2}s`
  }
}

async function handleRegister(e: MouseEvent) {
  // 基本验证
  if (!form.name) {
    ElMessage.warning('请输入姓名')
    return
  }
  if (!form.email) {
    ElMessage.warning('请输入邮箱')
    return
  }
  if (!form.password || form.password.length < 6) {
    ElMessage.warning('密码至少需要6个字符')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  // 涟漪效果
  const rect = (e.target as HTMLElement).getBoundingClientRect()
  rippleStyle.value = {
    left: `${(e as MouseEvent).clientX - rect.left}px`,
    top: `${(e as MouseEvent).clientY - rect.top}px`
  }
  ripple.value = true
  setTimeout(() => ripple.value = false, 600)

  loading.value = true
  try {
    const res = await userApi.register({
      name: form.name,
      email: form.email,
      password: form.password,
      phone: form.phone || undefined
    })

    if (res.data.success) {
      // 注册成功，自动登录
      userStore.setLoginData(res.data.data)
      ElMessage.success('注册成功')
      router.push('/')
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('注册失败：' + (e.response?.data?.error || e.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 引入特色字体 */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');

.register-page {
  min-height: 100vh;
  display: flex;
  background: #0a0e17;
  position: relative;
  overflow: hidden;
  font-family: 'Outfit', -apple-system, sans-serif;
}

/* 星空粒子 */
.starfield {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.star {
  position: absolute;
  background: #fff;
  border-radius: 50%;
  animation: twinkle ease-in-out infinite;
  opacity: 0;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.2); }
}

/* 渐变光晕 */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.5;
  animation: float 25s ease-in-out infinite;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #1e3a5f, #0d253f);
  top: -150px;
  left: -100px;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #2d1f47, #1a1030);
  bottom: -100px;
  right: 20%;
  animation-delay: -12s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(30px, -30px) rotate(3deg); }
  66% { transform: translate(-20px, 20px) rotate(-3deg); }
}

/* 主容器 */
.main-container {
  display: flex;
  width: 100%;
  min-height: 100vh;
  position: relative;
  z-index: 1;
  justify-content: center;
}

/* 左侧品牌区 */
.brand-section {
  width: 480px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #fff;
  animation: slide-in-left 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-in-left {
  from { opacity: 0; transform: translateX(-40px); }
  to { opacity: 1; transform: translateX(0); }
}

.brand-content {
  text-align: center;
  max-width: 420px;
}

.logo-mark {
  width: 48px;
  height: 48px;
  color: #63b3ed;
  margin: 0 auto 16px;
  animation: logo-float 4s ease-in-out infinite;
}

@keyframes logo-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.logo-mark svg {
  width: 100%;
  height: 100%;
}

.brand-name {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-tagline {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 28px;
  font-weight: 400;
  letter-spacing: 0.5px;
}

/* 特性四宫格 */
.features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.feature-item {
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  text-align: left;
  transition: all 0.3s;
  animation: fade-up 0.6s ease-out backwards;
}

.feature-item:nth-child(1) { animation-delay: 0.1s; }
.feature-item:nth-child(2) { animation-delay: 0.15s; }
.feature-item:nth-child(3) { animation-delay: 0.2s; }
.feature-item:nth-child(4) { animation-delay: 0.25s; }

@keyframes fade-up {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}

.feature-item:hover {
  background: rgba(99, 179, 237, 0.08);
  border-color: rgba(99, 179, 237, 0.2);
}

.feature-icon {
  width: 32px;
  height: 32px;
  background: rgba(99, 179, 237, 0.1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #63b3ed;
  margin-bottom: 10px;
}

.feature-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.feature-text h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 4px;
  color: #fff;
}

.feature-text p {
  font-size: 12px;
  margin: 0;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.5;
}

/* 品牌底部 */
.brand-footer {
  margin-top: 24px;
  text-align: center;
}

.stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, #63b3ed, #a5b4fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.copyright {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.2);
  margin: 0;
}

/* 右侧注册区 */
.register-section {
  width: 460px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  animation: slide-in-right 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-in-right {
  from { opacity: 0; transform: translateX(40px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 注册卡片 */
.register-card {
  width: 100%;
  max-width: 380px;
  padding: 36px;
  background: rgba(15, 20, 30, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.02) inset;
  position: relative;
  transition: transform 0.3s, box-shadow 0.3s;
}

.register-card:hover {
  transform: translateY(-2px);
}

.register-card.focused {
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 60px rgba(99, 179, 237, 0.1),
    0 0 0 1px rgba(99, 179, 237, 0.1) inset;
}

/* 卡片光晕边框 */
.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: 21px;
  background: linear-gradient(
    135deg,
    rgba(99, 179, 237, 0.3) 0%,
    transparent 40%,
    transparent 60%,
    rgba(147, 112, 219, 0.2) 100%
  );
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  -webkit-mask-composite: xor;
  padding: 1px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.register-card.focused .card-glow,
.register-card:hover .card-glow {
  opacity: 1;
}

/* 表单 */
.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-header {
  margin-bottom: 6px;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 6px;
}

.form-header p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

/* 输入字段 */
.field {
  position: relative;
}

.field.optional .optional-tag {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 400;
}

.field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: color 0.2s;
}

.field.active label {
  color: #63b3ed;
}

.input-wrap {
  position: relative;
}

.input-wrap input {
  width: 100%;
  padding: 14px 16px;
  padding-right: 44px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-family: inherit;
  outline: none;
  transition: all 0.2s;
}

.input-wrap input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.input-wrap input:focus {
  border-color: rgba(99, 179, 237, 0.4);
  background: rgba(99, 179, 237, 0.05);
}

/* 输入框光晕 */
.input-glow {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(99, 179, 237, 0.2);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
}

.field.active .input-glow {
  opacity: 1;
}

/* 密码可见切换 */
.toggle-pw {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
}

.toggle-pw:hover {
  color: rgba(255, 255, 255, 0.6);
}

.toggle-pw svg {
  width: 18px;
  height: 18px;
}

/* 字段提示 */
.field-hint {
  font-size: 12px;
  color: #f87171;
  margin-top: 6px;
}

/* 注册按钮 */
.submit-btn {
  position: relative;
  width: 100%;
  padding: 14px;
  margin-top: 6px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-text {
  position: relative;
  z-index: 1;
}

.btn-loader {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-loader::after {
  content: '';
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 按钮光效 */
.btn-glow {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
  animation: btn-shine 3s ease-in-out infinite;
}

@keyframes btn-shine {
  0%, 100% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
}

/* 涟漪效果 */
.ripple {
  position: absolute;
  width: 100px;
  height: 100px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0);
  animation: ripple 0.6s ease-out forwards;
  pointer-events: none;
}

@keyframes ripple {
  to { transform: translate(-50%, -50%) scale(4); opacity: 0; }
}

/* 表单底部 */
.form-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
}

.form-footer span {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

.form-footer a {
  font-size: 13px;
  color: #63b3ed;
  text-decoration: none;
  transition: color 0.2s;
}

.form-footer a:hover {
  color: #a5b4fc;
}

/* 响应式 */
@media (max-width: 1024px) {
  .main-container {
    flex-direction: column;
  }

  .brand-section {
    padding: 40px 30px;
    min-height: auto;
  }

  .features {
    display: none;
  }

  .stats {
    display: none;
  }

  .register-section {
    width: 100%;
    padding: 30px;
  }

  .brand-name {
    font-size: 32px;
  }
}

@media (max-width: 480px) {
  .register-card {
    padding: 32px 24px;
  }
}
</style>