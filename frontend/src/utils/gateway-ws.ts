/**
 * Gateway WebSocket 客户端
 * 完全参考 OpenClaw Control UI 实现
 * 源码: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/gateway.ts
 */

import * as ed from '@noble/ed25519'

// ==================== 类型定义 ====================

export type GatewayEventFrame = {
  type: 'event'
  event: string
  payload?: unknown
  seq?: number
}

export type GatewayResponseFrame = {
  type: 'res'
  id: string
  ok: boolean
  payload?: unknown
  error?: { code: string; message: string; details?: unknown }
}

export type GatewayHelloOk = {
  type: 'hello-ok'
  protocol: number
  auth?: {
    deviceToken?: string
    role?: string
    scopes?: string[]
  }
}

export type GatewayConnectDevice = {
  id: string
  publicKey: string
  signature: string
  signedAt: number
  nonce: string
}

type Pending = {
  resolve: (value: unknown) => void
  reject: (err: unknown) => void
}

// ==================== 设备身份管理 ====================

type StoredIdentity = {
  version: 1
  deviceId: string
  publicKey: string
  privateKey: string
  createdAtMs: number
}

export type DeviceIdentity = {
  deviceId: string
  publicKey: string
  privateKey: string
}

const STORAGE_KEY = 'openclaw-device-identity-v1'

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/g, '')
}

function base64UrlDecode(input: string): Uint8Array {
  const normalized = input.replaceAll('-', '+').replaceAll('_', '/')
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4)
  const binary = atob(padded)
  const out = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    out[i] = binary.charCodeAt(i)
  }
  return out
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

async function fingerprintPublicKey(publicKey: Uint8Array): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', publicKey.slice().buffer)
  return bytesToHex(new Uint8Array(hash))
}

async function generateIdentity(): Promise<DeviceIdentity> {
  const { secretKey, publicKey } = await ed.keygenAsync()
  const deviceId = await fingerprintPublicKey(publicKey)
  return {
    deviceId,
    publicKey: base64UrlEncode(publicKey),
    privateKey: base64UrlEncode(secretKey)
  }
}

async function loadOrCreateDeviceIdentity(): Promise<DeviceIdentity> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as StoredIdentity
      if (
        parsed?.version === 1 &&
        typeof parsed.deviceId === 'string' &&
        typeof parsed.publicKey === 'string' &&
        typeof parsed.privateKey === 'string'
      ) {
        const derivedId = await fingerprintPublicKey(base64UrlDecode(parsed.publicKey))
        if (derivedId !== parsed.deviceId) {
          const updated: StoredIdentity = {
            ...parsed,
            deviceId: derivedId
          }
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
          return {
            deviceId: derivedId,
            publicKey: parsed.publicKey,
            privateKey: parsed.privateKey
          }
        }
        return {
          deviceId: parsed.deviceId,
          publicKey: parsed.publicKey,
          privateKey: parsed.privateKey
        }
      }
    }
  } catch {
    // fall through to regenerate
  }

  const identity = await generateIdentity()
  const stored: StoredIdentity = {
    version: 1,
    deviceId: identity.deviceId,
    publicKey: identity.publicKey,
    privateKey: identity.privateKey,
    createdAtMs: Date.now()
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
  return identity
}

async function signDevicePayload(privateKeyBase64Url: string, payload: string): Promise<string> {
  const key = base64UrlDecode(privateKeyBase64Url)
  const data = new TextEncoder().encode(payload)
  const sig = await ed.signAsync(data, key)
  return base64UrlEncode(sig)
}

// ==================== 设备认证载荷 ====================

type DeviceAuthPayloadParams = {
  deviceId: string
  clientId: string
  clientMode: string
  role: string
  scopes: string[]
  signedAtMs: number
  token?: string | null
  nonce: string
}

function buildDeviceAuthPayload(params: DeviceAuthPayloadParams): string {
  const scopes = params.scopes.join(',')
  const token = params.token ?? ''
  return [
    'v2',
    params.deviceId,
    params.clientId,
    params.clientMode,
    params.role,
    scopes,
    String(params.signedAtMs),
    token,
    params.nonce
  ].join('|')
}

// ==================== Gateway 客户端 ====================

export class GatewayBrowserClient {
  private ws: WebSocket | null = null
  private pending = new Map<string, Pending>()
  private closed = false
  private connectNonce: string | null = null
  private connectSent = false
  private connectTimer: ReturnType<typeof setTimeout> | null = null
  private backoffMs = 800
  private deviceIdentity: DeviceIdentity | null = null
  private opts: {
    url: string
    token?: string
    onHello?: (hello: GatewayHelloOk) => void
    onEvent?: (evt: GatewayEventFrame) => void
    onClose?: (info: { code: number; reason: string; error?: { code: string; message: string } }) => void
  }

  constructor(opts: { url: string; token?: string; onHello?: (hello: GatewayHelloOk) => void; onEvent?: (evt: GatewayEventFrame) => void; onClose?: (info: { code: number; reason: string }) => void }) {
    this.opts = opts
  }

  async start() {
    this.closed = false

    // 加载或创建设备身份
    const isSecureContext = typeof crypto !== 'undefined' && !!crypto.subtle
    if (isSecureContext) {
      try {
        this.deviceIdentity = await loadOrCreateDeviceIdentity()
        console.log('[Gateway] Device identity loaded:', this.deviceIdentity.deviceId.slice(0, 8))
      } catch (err) {
        console.error('[Gateway] Failed to load device identity:', err)
      }
    }

    this.connect()
  }

  stop() {
    this.closed = true
    this.ws?.close()
    this.ws = null
    this.flushPending(new Error('gateway client stopped'))
  }

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private connect() {
    if (this.closed) return

    console.log('[Gateway] Connecting to', this.opts.url)
    this.ws = new WebSocket(this.opts.url)

    this.ws.addEventListener('open', () => {
      console.log('[Gateway] WebSocket open, waiting for challenge...')
      this.queueConnect()
    })

    this.ws.addEventListener('message', (ev) => {
      this.handleMessage(String(ev.data))
    })

    this.ws.addEventListener('close', (ev) => {
      const reason = String(ev.reason ?? '')
      console.log('[Gateway] WebSocket closed:', ev.code, reason)
      this.ws = null
      this.flushPending(new Error(`gateway closed (${ev.code}): ${reason}`))
      this.opts.onClose?.({ code: ev.code, reason })
      this.scheduleReconnect()
    })

    this.ws.addEventListener('error', () => {
      console.error('[Gateway] WebSocket error')
    })
  }

  private scheduleReconnect() {
    if (this.closed) return
    const delay = this.backoffMs
    this.backoffMs = Math.min(this.backoffMs * 1.7, 15000)
    console.log('[Gateway] Reconnecting in', delay, 'ms')
    setTimeout(() => this.connect(), delay)
  }

  private flushPending(err: Error) {
    for (const [, p] of this.pending) {
      p.reject(err)
    }
    this.pending.clear()
  }

  private queueConnect() {
    this.connectNonce = null
    this.connectSent = false

    if (this.connectTimer !== null) {
      clearTimeout(this.connectTimer)
    }

    this.connectTimer = setTimeout(() => {
      void this.sendConnect()
    }, 750)
  }

  private async buildDevice(): Promise<GatewayConnectDevice | undefined> {
    if (!this.deviceIdentity) return undefined

    const signedAtMs = Date.now()
    const nonce = this.connectNonce ?? ''
    const payload = buildDeviceAuthPayload({
      deviceId: this.deviceIdentity.deviceId,
      clientId: 'openclaw-control-ui',
      clientMode: 'ui',
      role: 'operator',
      scopes: ['operator.admin', 'operator.read', 'operator.write', 'operator.approvals', 'operator.pairing'],
      signedAtMs,
      token: this.opts.token ?? null,
      nonce
    })

    const signature = await signDevicePayload(this.deviceIdentity.privateKey, payload)

    return {
      id: this.deviceIdentity.deviceId,
      publicKey: this.deviceIdentity.publicKey,
      signature,
      signedAt: signedAtMs,
      nonce
    }
  }

  private async sendConnect() {
    if (this.connectSent) return
    this.connectSent = true

    if (this.connectTimer !== null) {
      clearTimeout(this.connectTimer)
      this.connectTimer = null
    }

    console.log('[Gateway] Sending connect request...')

    try {
      const device = await this.buildDevice()

      const hello = await this.request<GatewayHelloOk>('connect', {
        minProtocol: 3,
        maxProtocol: 3,
        client: {
          id: 'openclaw-control-ui',
          version: '1.0.0',
          platform: navigator.platform || 'web',
          mode: 'ui'
        },
        role: 'operator',
        scopes: ['operator.admin', 'operator.read', 'operator.write', 'operator.approvals', 'operator.pairing'],
        caps: ['tool-events'],
        auth: { token: this.opts.token },
        userAgent: navigator.userAgent,
        locale: navigator.language,
        device
      })

      console.log('[Gateway] Connect success:', hello)
      this.backoffMs = 800
      this.opts.onHello?.(hello)
    } catch (err: any) {
      console.error('[Gateway] Connect failed:', err)
      this.ws?.close(4008, 'connect failed')
    }
  }

  private handleMessage(raw: string) {
    let parsed: unknown
    try {
      parsed = JSON.parse(raw)
    } catch {
      return
    }

    const frame = parsed as { type?: unknown }

    if (frame.type === 'event') {
      const evt = parsed as GatewayEventFrame

      // 处理 connect.challenge
      if (evt.event === 'connect.challenge') {
        const payload = evt.payload as { nonce?: unknown } | undefined
        const nonce = payload && typeof payload.nonce === 'string' ? payload.nonce : null
        if (nonce) {
          console.log('[Gateway] Received challenge, nonce:', nonce.slice(0, 8))
          this.connectNonce = nonce
          void this.sendConnect()
        }
        return
      }

      this.opts.onEvent?.(evt)
      return
    }

    if (frame.type === 'res') {
      const res = parsed as GatewayResponseFrame
      const pending = this.pending.get(res.id)
      if (!pending) return
      this.pending.delete(res.id)
      if (res.ok) {
        pending.resolve(res.payload)
      } else {
        pending.reject(new Error(res.error?.message || 'request failed'))
      }
    }
  }

  async request<T = unknown>(method: string, params?: unknown): Promise<T> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('gateway not connected')
    }

    const id = crypto.randomUUID()
    const frame = { type: 'req', id, method, params }

    const p = new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: (v) => resolve(v as T), reject })
    })

    this.ws.send(JSON.stringify(frame))
    return p
  }
}

// ==================== Chat 事件处理 ====================

export type ChatState = {
  runId: string | null
  sessionKey: string
  state: 'delta' | 'final' | 'aborted' | 'error'
  message?: unknown
  errorMessage?: string
}

export function extractText(message: unknown): string | null {
  if (!message || typeof message !== 'object') return null
  const entry = message as Record<string, unknown>

  if (typeof entry.text === 'string') return entry.text

  const content = entry.content
  if (Array.isArray(content)) {
    const textBlock = content.find((block) => block?.type === 'text' && typeof block.text === 'string')
    if (textBlock) return textBlock.text
  }

  if (typeof content === 'string') return content

  return null
}

export function handleChatEvent(
  state: {
    chatMessages: any[]
    chatStream: string | null
    chatRunId: string | null
    lastError: string | null
    sessionKey: string
  },
  payload?: ChatState
): string | null {
  if (!payload) return null
  if (payload.sessionKey !== state.sessionKey) return null

  if (payload.state === 'delta') {
    const next = extractText(payload.message)
    if (typeof next === 'string') {
      const current = state.chatStream ?? ''
      if (!current || next.length >= current.length) {
        state.chatStream = next
      }
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || state.chatStream
    if (text?.trim()) {
      state.chatMessages = [
        ...state.chatMessages,
        {
          role: 'assistant',
          content: [{ type: 'text', text }],
          timestamp: Date.now()
        }
      ]
    }
    state.chatStream = null
    state.chatRunId = null
  } else if (payload.state === 'aborted') {
    const text = state.chatStream
    if (text?.trim()) {
      state.chatMessages = [
        ...state.chatMessages,
        {
          role: 'assistant',
          content: [{ type: 'text', text }],
          timestamp: Date.now()
        }
      ]
    }
    state.chatStream = null
    state.chatRunId = null
  } else if (payload.state === 'error') {
    state.chatStream = null
    state.chatRunId = null
    state.lastError = payload.errorMessage ?? 'chat error'
  }

  return payload.state
}

// ==================== 单例管理 ====================

let gatewayClient: GatewayBrowserClient | null = null

export function getGatewayClient(): GatewayBrowserClient | null {
  return gatewayClient
}

export function createGatewayClient(opts: {
  url: string
  token?: string
  onHello?: (hello: GatewayHelloOk) => void
  onEvent?: (evt: GatewayEventFrame) => void
  onClose?: (info: { code: number; reason: string }) => void
}): GatewayBrowserClient {
  if (gatewayClient) {
    gatewayClient.stop()
  }
  gatewayClient = new GatewayBrowserClient(opts)
  return gatewayClient
}