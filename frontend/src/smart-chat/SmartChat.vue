<template>
  <div class="organic-chat">
    <!-- 背景纹理 -->
    <div class="texture-layer">
      <svg class="noise" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <filter id="noise">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
        </filter>
        <rect width="100%" height="100%" filter="url(#noise)" opacity="0.03"/>
      </svg>
    </div>

    <!-- 浮动装饰 -->
    <div class="floating-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <!-- 左侧面板 -->
    <nav class="side-nav">
      <header class="nav-header">
        <div class="brand">
          <div class="brand-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 4C9.4 4 4 9.4 4 16s5.4 12 12 12 12-5.4 12-12S22.6 4 16 4z" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M16 10c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6z" fill="currentColor" opacity="0.2"/>
              <circle cx="16" cy="16" r="2" fill="currentColor"/>
            </svg>
          </div>
          <span class="brand-name">Dialogue</span>
        </div>
        <button class="add-circle" @click="showNewGroup = true" title="新建群聊">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
      </header>

      <div class="search-box">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input v-model="search" placeholder="搜索对话..." />
      </div>

      <div class="tab-pills">
        <button :class="['pill', { active: tab === 'single' }]" @click="tab = 'single'">
          <span class="pill-dot"></span>
          私聊
        </button>
        <button :class="['pill', { active: tab === 'group' }]" @click="tab = 'group'">
          <span class="pill-dot"></span>
          群聊
        </button>
      </div>

      <div class="contact-list">
        <!-- 私聊列表 -->
        <template v-if="tab === 'single'">
          <div
            v-for="(a, i) in filteredAgents"
            :key="a.id"
            :class="['contact-item', { selected: selType === 'single' && selId === a.id }]"
            :style="{ '--i': i }"
            @click="pick('single', a.id)"
          >
            <div class="avatar-ring" :style="ringColor(a.id)">
              <div class="avatar" :style="avatarColor(a.id)">
                {{ a.name?.charAt(0) || '?' }}
              </div>
            </div>
            <div class="contact-info">
              <div class="contact-top">
                <span class="contact-name">{{ a.name }}</span>
                <span class="contact-time" v-if="a.lastTime">{{ shortTime(a.lastTime) }}</span>
              </div>
              <div class="contact-bottom">
                <span class="contact-preview">{{ a.lastMessage || '开始新对话' }}</span>
                <span class="unread-badge" v-if="a.unread">{{ a.unread > 99 ? '99+' : a.unread }}</span>
              </div>
            </div>
          </div>
        </template>
        <!-- 群聊列表 -->
        <template v-else>
          <div
            v-for="(g, i) in filteredGroups"
            :key="g.id"
            :class="['contact-item', { selected: selType === 'group' && selId === g.id }]"
            :style="{ '--i': i }"
            @click="pick('group', g.id)"
          >
            <div class="avatar-ring group-ring">
              <div class="avatar group-av">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
            </div>
            <div class="contact-info">
              <div class="contact-top">
                <span class="contact-name">{{ g.name }}</span>
                <span class="contact-time" v-if="g.lastTime">{{ shortTime(g.lastTime) }}</span>
              </div>
              <div class="contact-bottom">
                <span class="contact-preview">{{ g.lastMessage || `${g.members.length} 位成员` }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <template v-if="active">
        <!-- 顶栏 -->
        <header class="content-header">
          <div class="header-left">
            <div class="avatar-ring" :style="selType === 'single' ? ringColor(agent?.id) : {}">
              <div class="avatar" v-if="selType === 'single'" :style="avatarColor(agent?.id)">
                {{ agent?.name?.charAt(0) || '?' }}
              </div>
              <div class="avatar group-av" v-else>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                </svg>
              </div>
            </div>
            <div class="header-info">
              <h2 class="header-title">{{ title }}</h2>
              <p class="header-sub" v-if="selType === 'group' && curGroup">
                {{ curGroup.members.map(m => m.name).join(' · ') }}
              </p>
            </div>
          </div>
          <button class="info-toggle" @click="showDetail = !showDetail">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4M12 8h.01"/>
            </svg>
          </button>
        </header>

        <!-- 消息区 -->
        <div class="messages-container" ref="msgRef">
          <!-- 欢迎 -->
          <div v-if="msgs.length === 0" class="welcome-state">
            <div class="welcome-avatar-wrap" :style="selType === 'single' ? ringColor(agent?.id) : {}">
              <div class="welcome-avatar" :style="selType === 'single' ? avatarColor(agent?.id) : {}">
                <template v-if="selType === 'single'">{{ agent?.name?.charAt(0) }}</template>
                <template v-else>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </template>
              </div>
            </div>
            <h3 class="welcome-name">{{ title }}</h3>
            <p class="welcome-hint" v-if="selType === 'single'">与 {{ agent?.name }} 开始对话</p>
            <p class="welcome-hint" v-else>群聊协作模式，主持人协调各 Agent</p>
          </div>

          <!-- 消息 -->
          <div v-for="(m, i) in msgs" :key="m.id" :class="['message', m.role]" :style="{ '--i': i }">
            <div class="message-avatar" :style="avatarColor(m.role === 'user' ? 'user' : m.sourceAgent)">
              {{ senderLabel(m).charAt(0) }}
            </div>
            <div class="message-body">
              <div class="message-meta">
                <span class="message-sender">{{ senderLabel(m) }}</span>
                <span class="message-time">{{ clock(m.timestamp) }}</span>
              </div>
              <div class="message-content" v-html="md(textOf(m))"></div>
            </div>
          </div>

          <!-- 流式输出 -->
          <div v-if="streaming && stream" class="message assistant streaming" :style="{ '--i': msgs.length }">
            <div class="message-avatar" :style="avatarColor(agent?.id)">
              {{ agent?.name?.charAt(0) || '?' }}
            </div>
            <div class="message-body">
              <div class="message-meta">
                <span class="message-sender">{{ agent?.name }}</span>
                <span class="typing-indicator">
                  <i></i><i></i><i></i>
                </span>
              </div>
              <div class="message-content" v-html="md(stream)"></div>
            </div>
          </div>

          <div ref="bottomRef"></div>
        </div>

        <!-- 输入区 -->
        <footer class="input-footer">
          <div class="input-wrapper">
            <textarea
              ref="taRef"
              v-model="input"
              :disabled="streaming"
              placeholder="输入消息..."
              rows="1"
              @keydown="onKey"
              @input="grow"
            />
            <button class="send-circle" :class="{ ready: canGo }" :disabled="!canGo || streaming" @click="send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </footer>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-illustration">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <h3>选择一个对话</h3>
        <p>从左侧列表选择联系人或群聊开始</p>
      </div>
    </main>

    <!-- 详情面板 -->
    <Transition name="slide">
      <aside v-if="showDetail" class="detail-panel">
        <header class="detail-header">
          <h3>信息</h3>
          <button class="close-btn" @click="showDetail = false">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </header>
        <div class="detail-content" v-if="selType === 'group' && curGroup">
          <section class="detail-section">
            <h4>主持人</h4>
            <div class="member-card host">
              <div class="member-avatar" :style="avatarColor(curGroup.hostId)">{{ curGroup.hostName.charAt(0) }}</div>
              <span class="member-name">{{ curGroup.hostName }}</span>
              <span class="member-tag">HOST</span>
            </div>
          </section>
          <section class="detail-section">
            <h4>成员 · {{ curGroup.members.length }}</h4>
            <div class="member-card" v-for="m in curGroup.members" :key="m.agentId">
              <div class="member-avatar" :style="avatarColor(m.agentId)">{{ m.name.charAt(0) }}</div>
              <span class="member-name">{{ m.name }}</span>
            </div>
          </section>
        </div>
        <div class="detail-content" v-else-if="selType === 'single' && agent">
          <section class="detail-section">
            <h4>Agent 信息</h4>
            <div class="info-row"><span class="label">名称</span><span class="value">{{ agent.name }}</span></div>
            <div class="info-row"><span class="label">模型</span><span class="value">{{ agent.model || '-' }}</span></div>
            <div class="info-row"><span class="label">ID</span><span class="value mono">{{ agent.id }}</span></div>
          </section>
        </div>
      </aside>
    </Transition>

    <!-- 新建群聊弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showNewGroup" class="modal-overlay" @click.self="showNewGroup = false">
          <div class="modal-card">
            <header class="modal-header">
              <h3>创建群聊</h3>
              <button class="close-btn" @click="showNewGroup = false">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
              </button>
            </header>
            <div class="modal-body">
              <label class="field">
                <span>群名称</span>
                <input v-model="ngName" placeholder="为群聊命名" />
              </label>
              <label class="field">
                <span>主持人</span>
                <div class="chip-grid">
                  <div
                    v-for="a in agents"
                    :key="a.id"
                    :class="['chip', { selected: ngHost === a.id }]"
                    @click="ngHost = a.id"
                  >
                    <div class="chip-avatar" :style="avatarColor(a.id)">{{ a.name.charAt(0) }}</div>
                    {{ a.name }}
                  </div>
                </div>
              </label>
              <label class="field">
                <span>成员</span>
                <div class="chip-grid">
                  <div
                    v-for="a in agents.filter(x => x.id !== ngHost)"
                    :key="a.id"
                    :class="['chip', { selected: ngParts.includes(a.id) }]"
                    @click="toggle(a.id)"
                  >
                    <div class="chip-avatar" :style="avatarColor(a.id)">{{ a.name.charAt(0) }}</div>
                    {{ a.name }}
                  </div>
                </div>
              </label>
            </div>
            <footer class="modal-footer">
              <button class="btn-outline" @click="showNewGroup = false">取消</button>
              <button class="btn-primary" :disabled="!okGroup" @click="makeGroup">创建</button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '../user/stores'
import { agentApi } from '../api'
import { createGatewayClient, getGatewayClient, extractText } from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { Message } from './types'

interface GroupChat {
  id: string
  name: string
  hostId: string
  hostName: string
  members: { agentId: string; name: string; enabled: boolean }[]
  lastMessage?: string
  lastTime?: number
}

interface AgentConv {
  id: string
  name: string
  model?: string
  lastMessage?: string
  lastTime?: number
  unread?: number
}

const userStore = useUserStore()
const agents = ref<AgentConv[]>([])
const groups = ref<GroupChat[]>([])
const search = ref('')
const tab = ref<'single' | 'group'>('single')
const selType = ref<'single' | 'group' | null>(null)
const selId = ref('')
const showDetail = ref(false)
const showNewGroup = ref(false)
const msgs = ref<Message[]>([])
const msgsMap = ref<Map<string, Message[]>>(new Map())
const streaming = ref(false)
const stream = ref('')
const input = ref('')
const taRef = ref<HTMLTextAreaElement | null>(null)
const msgRef = ref<HTMLElement | null>(null)
const bottomRef = ref<HTMLElement | null>(null)
const ngName = ref('')
const ngHost = ref('')
const ngParts = ref<string[]>([])
let client: ReturnType<typeof createGatewayClient> | null = null
const sessMap = ref<Map<string, string>>(new Map())

const active = computed(() => selType.value !== null)
const agent = computed(() => agents.value.find(a => a.id === selId.value))
const curGroup = computed(() => groups.value.find(g => g.id === selId.value))
const title = computed(() => {
  if (selType.value === 'single') return agent.value?.name || '对话'
  if (selType.value === 'group') return curGroup.value?.name || '群聊'
  return ''
})
const canGo = computed(() => input.value.trim().length > 0)
const okGroup = computed(() => ngHost.value && ngParts.value.length > 0)

const filteredAgents = computed(() => {
  if (!search.value) return agents.value
  return agents.value.filter(a => a.name.toLowerCase().includes(search.value.toLowerCase()))
})
const filteredGroups = computed(() => {
  if (!search.value) return groups.value.filter(g => g.name.toLowerCase().includes(search.value.toLowerCase()))
  return groups.value
})

// ========== 配色系统 ==========
const palette = [
  { ring: '#d4a373', bg: 'linear-gradient(135deg, #d4a373, #bc6c25)' },
  { ring: '#81b29a', bg: 'linear-gradient(135deg, #81b29a, #52b788)' },
  { ring: '#e07a5f', bg: 'linear-gradient(135deg, #e07a5f, #d62828)' },
  { ring: '#3d5a80', bg: 'linear-gradient(135deg, #3d5a80, #293241)' },
  { ring: '#9c6644', bg: 'linear-gradient(135deg, #9c6644, #7f5539)' },
  { ring: '#6b705c', bg: 'linear-gradient(135deg, #6b705c, #474739)' },
  { ring: '#cb997e', bg: 'linear-gradient(135deg, #cb997e, #a57548)' },
  { ring: '#588157', bg: 'linear-gradient(135deg, #588157, #3a5a40)' },
]

function colorIdx(id?: string): number {
  if (!id) return 0
  return id.split('').reduce((s, c) => s + c.charCodeAt(0), 0) % palette.length
}

function ringColor(id?: string) {
  return { '--ring': palette[colorIdx(id)].ring }
}

function avatarColor(id?: string) {
  return { background: palette[colorIdx(id)].bg }
}

// ========== 核心逻辑 ==========
function pick(type: 'single' | 'group', id: string) {
  selType.value = type
  selId.value = id
  const key = `${type}-${id}`
  msgs.value = msgsMap.value.get(key) || []
  scrollTo(false)
  ensureSession(key, type === 'single' ? id : curGroup.value!.hostId, type === 'group')
}

async function ensureSession(key: string, agentId: string, isGroup = false) {
  if (!client?.connected) return
  if (sessMap.value.has(key)) return
  const sid = crypto.randomUUID()
  const sk = isGroup ? `agent:${agentId}:groupchat:${sid}` : `agent:${agentId}:webchat:${sid}`
  sessMap.value.set(key, sk)
  try { await client!.request('sessions.subscribe', { keys: [sk] }) } catch (e) { console.error(e) }
}

function senderLabel(m: Message): string {
  if (m.sourceName) return m.sourceName
  if (m.role === 'user') return userStore.user?.display_name || '你'
  return agent.value?.name || 'Assistant'
}

function textOf(m: Message): string {
  return Array.isArray(m.content) ? m.content.find(c => c.type === 'text')?.text || '' : ''
}

function md(t: string): string { return renderMessageContent(t) }

function clock(ts?: number): string {
  return ts ? new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''
}

function shortTime(ts?: number): string {
  if (!ts) return ''
  const d = new Date(ts), n = new Date()
  return d.toDateString() === n.toDateString()
    ? d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
}

function grow() {
  const ta = taRef.value
  if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 120) + 'px' }
}

async function send() {
  if (!canGo.value || !client || streaming.value) return
  const content = input.value.trim()
  input.value = ''; grow()

  const key = `${selType.value}-${selId.value}`
  const um: Message = {
    id: crypto.randomUUID(), role: 'user',
    content: [{ type: 'text', text: content }], timestamp: Date.now()
  }
  const arr = msgsMap.value.get(key) || []
  arr.push(um)
  msgsMap.value.set(key, [...arr])
  msgs.value = [...arr]

  if (selType.value === 'single') {
    const a = agents.value.find(x => x.id === selId.value)
    if (a) { a.lastMessage = content.slice(0, 30); a.lastTime = Date.now() }
  } else if (curGroup.value) {
    curGroup.value.lastMessage = content.slice(0, 30)
    curGroup.value.lastTime = Date.now()
  }

  let sk = sessMap.value.get(key)
  if (!sk) {
    await ensureSession(key, selType.value === 'single' ? selId.value : curGroup.value!.hostId, selType.value === 'group')
    sk = sessMap.value.get(key)
  }
  if (!sk) return

  let body = content
  if (selType.value === 'group' && curGroup.value) {
    const g = curGroup.value
    const info = g.members.filter(m => m.enabled).map(m => `- ${m.name}(${m.agentId})`).join('\n')
    body = `【群聊上下文】\n主持人：${g.hostName}\n参与者：\n${info}\n\n【用户问题】\n${content}\n\n请根据问题决定需要哪些 Agent 参与，并使用 sessions_send 工具与他们讨论。`
  }

  streaming.value = true; stream.value = ''
  try {
    await client.request('chat.send', { sessionKey: sk, message: body, deliver: false, idempotencyKey: crypto.randomUUID() })
  } catch (e: any) { streaming.value = false; console.error(e) }
}

function scrollTo(smooth = true) {
  nextTick(() => {
    if (msgRef.value) msgRef.value.scrollTo({ top: msgRef.value.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  })
}

function toggle(id: string) {
  const i = ngParts.value.indexOf(id)
  if (i >= 0) ngParts.value.splice(i, 1)
  else ngParts.value.push(id)
}

function makeGroup() {
  const host = agents.value.find(a => a.id === ngHost.value)
  const members = ngParts.value.map(id => {
    const a = agents.value.find(x => x.id === id)
    return { agentId: id, name: a?.name || id, enabled: true }
  })
  const g: GroupChat = {
    id: `g-${crypto.randomUUID()}`,
    name: ngName.value || `${host?.name || '群'}的群`,
    hostId: ngHost.value, hostName: host?.name || ngHost.value, members
  }
  groups.value.unshift(g)
  showNewGroup.value = false
  ngName.value = ''; ngHost.value = ''; ngParts.value = []
  pick('group', g.id); persist()
}

function persist() {
  localStorage.setItem('dialogue-chat-v1', JSON.stringify({ groups: groups.value, msgs: Object.fromEntries(msgsMap.value) }))
}

function hydrate() {
  try {
    const raw = localStorage.getItem('dialogue-chat-v1')
    if (raw) {
      const d = JSON.parse(raw)
      groups.value = d.groups || []
      if (d.msgs) msgsMap.value = new Map(Object.entries(d.msgs))
    }
  } catch (e) { console.error(e) }
}

function onEvent(evt: any) {
  if (evt.event !== 'chat') return
  const p = evt.payload, sk = p.sessionKey
  let key: string | null = null
  for (const [k, v] of sessMap.value.entries()) { if (v === sk) { key = k; break } }
  if (!key) return

  if (p.state === 'delta') {
    const t = extractText(p.message)
    if (typeof t === 'string') { stream.value = t; scrollTo() }
  } else if (p.state === 'final') {
    const t = extractText(p.message) || stream.value
    if (t?.trim()) {
      const m: Message = { id: crypto.randomUUID(), role: 'assistant', content: [{ type: 'text', text: t }], timestamp: Date.now() }
      const arr = msgsMap.value.get(key) || []
      arr.push(m); msgsMap.value.set(key, [...arr])
      if (key === `${selType.value}-${selId.value}`) msgs.value = [...arr]

      if (key.startsWith('single-')) {
        const a = agents.value.find(x => x.id === key.replace('single-', ''))
        if (a) { a.lastMessage = t.slice(0, 30); a.lastTime = Date.now() }
      } else {
        const g = groups.value.find(x => x.id === key.replace('group-', ''))
        if (g) { g.lastMessage = t.slice(0, 30); g.lastTime = Date.now() }
      }
    }
    stream.value = ''; streaming.value = false; scrollTo(); persist()
  } else if (p.state === 'error') {
    stream.value = ''; streaming.value = false; console.error(p.errorMessage)
  }
}

onMounted(async () => {
  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = (res.data.data || []).map((a: any) => ({
        id: a.id, name: a.name || a.id, model: a.model, lastMessage: '', lastTime: 0, unread: 0
      }))
    }
  } catch (e) { console.error(e) }

  hydrate()

  // 检查是否已有 Gateway 连接
  const existingClient = getGatewayClient()
  if (existingClient && existingClient.connected) {
    console.log('[Dialogue] Reusing existing Gateway connection')
    client = existingClient
    ;(client as any).opts.onEvent = onEvent
  } else {
    try {
      const { chatApi } = await import('../api')
      const res = await chatApi.getConfig()
      if (res.data.success) {
        const { gatewayUrl, gatewayToken } = res.data.data
        client = createGatewayClient({
          url: gatewayUrl, token: gatewayToken,
          onHello: () => console.log('[Dialogue] connected'),
          onEvent, onClose: () => console.log('[Dialogue] closed')
        })
        client.start()
      }
    } catch (e) { console.error(e) }
  }
})

// 不停止 Gateway 连接，让其他组件复用
onUnmounted(() => { persist() })
watch(msgs, () => scrollTo())
</script>

<style scoped>
/* ========== 设计系统 ========== */
.organic-chat {
  --bg: #faf9f7;
  --surface: #ffffff;
  --surface-alt: #f5f3f0;
  --text: #2d2a26;
  --text-muted: #7a7672;
  --text-dim: #b8b4af;
  --border: #e8e5e1;
  --border-light: #f0ede9;
  --accent: #81b29a;
  --accent-soft: rgba(129, 178, 154, 0.12);
  --warm: #d4a373;

  position: relative;
  display: flex;
  height: 100%;
  background: var(--bg);
  font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--text);
  overflow: hidden;
}

/* ========== 背景纹理 ========== */
.texture-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.4;
}

.noise {
  width: 100%;
  height: 100%;
}

/* ========== 浮动装饰 ========== */
.floating-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
  animation: drift 25s ease-in-out infinite;
}

.shape-1 {
  width: 300px;
  height: 300px;
  background: var(--accent);
  top: -50px;
  right: 10%;
  animation-delay: 0s;
}

.shape-2 {
  width: 200px;
  height: 200px;
  background: var(--warm);
  bottom: 20%;
  left: -30px;
  animation-delay: -8s;
}

.shape-3 {
  width: 150px;
  height: 150px;
  background: #6b705c;
  top: 50%;
  right: -20px;
  animation-delay: -16s;
}

@keyframes drift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(20px, -20px) scale(1.05); }
  50% { transform: translate(-10px, 10px) scale(0.95); }
  75% { transform: translate(15px, 15px) scale(1.02); }
}

/* ========== 左侧导航 ========== */
.side-nav {
  width: 280px;
  background: var(--surface);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
}

.nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  color: var(--accent);
}

.brand-name {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.add-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
}

.add-circle:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 12px 12px;
  padding: 10px 14px;
  background: var(--surface-alt);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.search-box:focus-within {
  background: var(--surface);
  box-shadow: 0 0 0 1px var(--border);
}

.search-box svg { color: var(--text-dim); flex-shrink: 0; }

.search-box input {
  flex: 1;
  background: none;
  border: none;
  font-size: 13px;
  color: var(--text);
  font-family: inherit;
}

.search-box input::placeholder { color: var(--text-dim); }
.search-box input:focus { outline: none; }

.tab-pills {
  display: flex;
  gap: 6px;
  padding: 0 12px 12px;
}

.pill {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px;
  border-radius: 10px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.pill:hover { color: var(--text); }

.pill.active {
  background: var(--accent-soft);
  color: var(--accent);
}

.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.pill.active .pill-dot { opacity: 1; }

.contact-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.contact-list::-webkit-scrollbar { width: 4px; }
.contact-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin: 2px 4px;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  animation: slideIn 0.3s ease backwards;
  animation-delay: calc(var(--i) * 0.02s);
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

.contact-item:hover { background: var(--surface-alt); }

.contact-item.selected {
  background: var(--accent-soft);
}

.avatar-ring {
  position: relative;
  flex-shrink: 0;
}

.avatar-ring::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 12px;
  border: 2px solid var(--ring, var(--accent));
  opacity: 0;
  transition: opacity 0.2s ease;
}

.contact-item:hover .avatar-ring::before,
.contact-item.selected .avatar-ring::before { opacity: 0.5; }

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  position: relative;
}

.group-av {
  background: linear-gradient(135deg, var(--surface-alt), #e0ddd8);
  color: var(--text-muted);
}

.group-ring::before { border-color: var(--text-dim); }

.contact-info { flex: 1; min-width: 0; }

.contact-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.contact-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.contact-time {
  font-size: 10px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}

.contact-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}

.contact-preview {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unread-badge {
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

/* ========== 主内容区 ========== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
  z-index: 5;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(250, 249, 247, 0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-info { display: flex; flex-direction: column; gap: 2px; }

.header-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.header-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.info-toggle {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.info-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* ========== 消息区 ========== */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.messages-container::-webkit-scrollbar { width: 5px; }
.messages-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

.welcome-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  animation: fadeUp 0.5s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.welcome-avatar-wrap {
  position: relative;
}

.welcome-avatar-wrap::before {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 24px;
  border: 2px solid var(--ring, var(--accent));
  opacity: 0.3;
  animation: breathe 3s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.05); opacity: 0.5; }
}

.welcome-avatar {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 600;
  color: #fff;
  position: relative;
}

.welcome-name {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.welcome-hint {
  font-size: 13px;
  color: var(--text-muted);
}

/* 消息样式 */
.message {
  display: flex;
  gap: 12px;
  animation: messageIn 0.3s ease backwards;
  animation-delay: calc(var(--i) * 0.02s);
}

@keyframes messageIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user { flex-direction: row-reverse; }

.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.message-body { max-width: 65%; }

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.message.user .message-meta { flex-direction: row-reverse; }

.message-sender {
  font-size: 12px;
  font-weight: 500;
}

.message-time {
  font-size: 10px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}

.typing-indicator {
  display: inline-flex;
  gap: 3px;
  align-items: center;
}

.typing-indicator i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent);
  animation: typing 1s ease infinite;
}

.typing-indicator i:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator i:nth-child(3) { animation-delay: 0.3s; }

@keyframes typing {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.message-content {
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: 14px;
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.message.user .message-content {
  background: var(--accent-soft);
  border-color: transparent;
}

.message-content :deep(p) { margin: 0; }
.message-content :deep(p + p) { margin-top: 8px; }
.message-content :deep(code) {
  background: var(--surface-alt);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.message-content :deep(pre) {
  background: var(--surface-alt);
  padding: 12px;
  border-radius: 8px;
  margin: 8px 0;
  overflow-x: auto;
}
.message-content :deep(pre code) {
  background: none;
  padding: 0;
}

.message.streaming .message-content {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(129, 178, 154, 0.15);
}

/* ========== 输入区 ========== */
.input-footer {
  padding: 16px 24px;
  background: rgba(250, 249, 247, 0.8);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-light);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  transition: all 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(129, 178, 154, 0.1);
}

.input-wrapper textarea {
  flex: 1;
  background: none;
  border: none;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text);
  resize: none;
  min-height: 20px;
  max-height: 120px;
  font-family: inherit;
}

.input-wrapper textarea::placeholder { color: var(--text-dim); }
.input-wrapper textarea:focus { outline: none; }
.input-wrapper textarea:disabled { opacity: 0.5; }

.send-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--surface-alt);
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  flex-shrink: 0;
}

.send-circle.ready {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 4px 16px rgba(129, 178, 154, 0.3);
}

.send-circle.ready:hover { transform: scale(1.05); }
.send-circle:disabled { cursor: not-allowed; opacity: 0.4; }

/* ========== 空状态 ========== */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.empty-illustration {
  width: 100px;
  height: 100px;
  border-radius: 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-dim);
  animation: breathe 3s ease-in-out infinite;
}

.empty-state h3 {
  font-size: 18px;
  font-weight: 600;
}

.empty-state p {
  font-size: 13px;
  color: var(--text-muted);
}

/* ========== 详情面板 ========== */
.detail-panel {
  width: 280px;
  background: var(--surface);
  border-left: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 10;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}

.detail-header h3 {
  font-size: 14px;
  font-weight: 600;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.close-btn:hover { background: var(--surface-alt); color: var(--text); }

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.detail-section { margin-bottom: 24px; }

.detail-section h4 {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 12px;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.member-card.host {
  background: var(--accent-soft);
  margin: 0 -12px;
  padding: 8px 12px;
  border-radius: 10px;
}

.member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

.member-name {
  flex: 1;
  font-size: 13px;
}

.member-tag {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--accent);
  color: #fff;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.info-row .label { font-size: 12px; color: var(--text-muted); }
.info-row .value { font-size: 12px; }
.info-row .value.mono { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text-dim); }

.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); opacity: 0; }

/* ========== 弹窗 ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(45, 42, 38, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-card {
  width: 420px;
  background: var(--surface);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(45, 42, 38, 0.15);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.modal-body { padding: 24px; }

.field {
  display: block;
  margin-bottom: 20px;
}

.field > span {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.field input {
  width: 100%;
  padding: 12px 16px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 13px;
  color: var(--text);
  font-family: inherit;
  transition: all 0.2s ease;
}

.field input:focus { outline: none; border-color: var(--accent); }

.chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px 8px 8px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}

.chip:hover { border-color: var(--accent); color: var(--text); }

.chip.selected {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

.chip-avatar {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-light);
}

.btn-outline {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-outline:hover { background: var(--surface-alt); color: var(--text); }

.btn-primary {
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-primary:hover { box-shadow: 0 4px 12px rgba(129, 178, 154, 0.3); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

.modal-enter-active, .modal-leave-active { transition: all 0.3s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card, .modal-leave-to .modal-card { transform: scale(0.95) translateY(10px); }
</style>