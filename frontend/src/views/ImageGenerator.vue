<template>
  <div class="studio">
    <!-- 背景装饰 -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <!-- 生成结果 -->
    <transition name="slide-up">
      <div v-if="loading || images.length > 0" class="result-area">
        <div v-if="loading" class="loading-canvas">
          <div class="loading-rings">
            <div class="ring"></div>
            <div class="ring"></div>
            <div class="ring"></div>
          </div>
          <p class="loading-text">AI 正在创作中<span class="dots"><span>.</span><span>.</span><span>.</span></span></p>
        </div>
        <div v-else class="images-gallery">
          <div
            v-for="(img, i) in images"
            :key="i"
            class="gallery-item"
            :style="{ animationDelay: `${i * 0.1}s` }"
          >
            <img :src="img.url" @click="openImage(img.url)" />
            <div class="gallery-overlay">
              <button class="dl-btn" @click="download(img.url, i)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 创作区 -->
    <div class="creator">
      <div class="prompt-wrap">
        <textarea
          v-model="prompt"
          class="prompt-input"
          placeholder="描述你脑海中的画面，让 AI 为你创作..."
          rows="3"
          @keydown.ctrl.enter="generate"
        ></textarea>
        <button
          class="gen-btn"
          :class="{ loading }"
          :disabled="loading || !prompt.trim()"
          @click="generate"
        >
          <span v-if="!loading">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            生成
          </span>
          <span v-else class="btn-loading"></span>
        </button>
      </div>

      <div class="options-row">
        <div class="templates">
          <span
            v-for="(text, key) in templates"
            :key="key"
            :class="['tpl-tag', { active: selectedTemplate === key }]"
            @click="applyTemplate(key)"
          >{{ templateNames[key] }}</span>
        </div>
        <div class="controls">
          <div class="ctrl-group">
            <span class="ctrl-label">尺寸</span>
            <div class="ctrl-btns">
              <button :class="['ctrl-btn', { active: size === '2k' }]" @click="size = '2k'">2K</button>
              <button :class="['ctrl-btn', { active: size === '4k' }]" @click="size = '4k'">4K</button>
            </div>
          </div>
          <div class="ctrl-group">
            <span class="ctrl-label">数量</span>
            <div class="ctrl-btns">
              <button v-for="num in [1,2,3,4]" :key="num" :class="['ctrl-btn', { active: n === num }]" @click="n = num">{{ num }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const prompt = ref('')
const size = ref('2k')
const n = ref(1)
const loading = ref(false)
const images = ref<{ url: string }[]>([])
const selectedTemplate = ref('')

const templateNames: Record<string, string> = {
  office: '办公场景', logo: '游戏Logo', poster: '产品海报', oil_painting: '油画风格',
  fridge: '冰箱内部', diagram: '教学图表', sci_fi: '科幻场景',
  landscape: '自然风景', portrait: '人物肖像', product: '电商产品'
}

const templates: Record<string, string> = {
  office: '一个凌乱的办公桌桌面。桌面上有一台开着的笔记本电脑，屏幕显示代码；旁边一个马克杯，杯上写着"Developer"，杯口冒着热气；一本摊开的书；一个便签贴；一支钢笔。阳光从右侧照射，在桌上形成光影。',
  logo: '设计一个科技公司的 logo，主体是一只蓝色的狐狸，狐狸眼睛是绿色的像素点，logo 上写有公司名 "TechFox"，简约现代风格。',
  poster: '设计一张产品发布会海报，标题为 "新品发布"，背景是深蓝色渐变，中心是悬浮的产品手机，四周有光效粒子，底部写着 "2026年4月"。',
  oil_painting: '一个穿着华丽服装的女孩，撑着遮阳伞走在林荫道上，莫奈油画风格，柔和的光影，细腻的笔触。',
  fridge: '冰箱打开的内部视图：上层放着牛奶和鸡蛋，中层是烤鸡和草莓保鲜盒，下层蔬菜抽屉里有生菜和西红柿，门后置物架放着番茄酱。',
  diagram: '一张教学图表，展示维恩图的三个圆交集关系，三个圆分别为灰色、蓝色和浅绿色，圆上标注"集合A"、"集合B"、"集合C"，背景简洁。',
  sci_fi: '一个未来城市的街景，高耸的玻璃建筑，空中悬浮的交通工具，霓虹灯招牌写着"NeoCity"，夜晚雨后反射的灯光，赛博朋克风格。',
  landscape: '一片宁静的湖泊，远处是雪山，湖面倒映着山峰，清晨的金色阳光穿过云层，岸边的松树，高清摄影风格。',
  portrait: '一位年轻的女性肖像，柔和的自然光线，微笑的表情，简约的背景，专业的摄影风格，高清晰度。',
  product: '一款高端耳机产品展示图，耳机主体是黑色金属质感，耳罩有银色边框，背景是深色渐变，产品正面悬浮展示，电商广告风格。'
}

function applyTemplate(key: string) {
  selectedTemplate.value = key
  prompt.value = templates[key]
}

async function generate() {
  if (!prompt.value.trim()) return
  loading.value = true
  images.value = []
  try {
    const res = await api.post('/image-generator/generate', {
      prompt: prompt.value, size: size.value, n: n.value
    }, { timeout: 60000 })
    if (res.data.success && res.data.data?.images) {
      images.value = res.data.data.images
      ElMessage.success(`成功生成 ${images.value.length} 张图片`)
    } else {
      ElMessage.error(res.data.error || '生成失败')
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '请求失败')
  } finally {
    loading.value = false
  }
}

function openImage(url: string) { window.open(url, '_blank') }

async function download(url: string, index: number) {
  try {
    const resp = await fetch(url)
    const blob = await resp.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `image-${index + 1}.png`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('下载成功')
  } catch { ElMessage.error('下载失败') }
}
</script>

<style scoped>
.studio {
  min-height: calc(100vh - 120px);
  padding: 32px 40px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* 背景光晕 */
.bg-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.12;
  pointer-events: none;
  z-index: 0;
}
.orb-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #6366f1, transparent);
  top: -100px; right: -100px;
  animation: float 8s ease-in-out infinite;
}
.orb-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #ec4899, transparent);
  bottom: 0; left: -80px;
  animation: float 10s ease-in-out infinite reverse;
}
.orb-3 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #06b6d4, transparent);
  top: 40%; left: 40%;
  animation: float 12s ease-in-out infinite 3s;
}

/* 结果区 */
.result-area {
  position: relative;
  z-index: 1;
}

/* 加载动画 */
.loading-canvas {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  gap: 24px;
}
.loading-rings {
  position: relative;
  width: 64px;
  height: 64px;
}
.ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid transparent;
  animation: spin 1.5s linear infinite;
}
.ring:nth-child(1) { border-top-color: #6366f1; animation-duration: 1.2s; }
.ring:nth-child(2) { inset: 8px; border-top-color: #ec4899; animation-duration: 1.8s; animation-direction: reverse; }
.ring:nth-child(3) { inset: 16px; border-top-color: #06b6d4; animation-duration: 2.4s; }

.loading-text {
  font-size: 15px;
  color: #888;
  letter-spacing: 0.5px;
}
.dots span {
  animation: blink 1.4s infinite;
  opacity: 0;
}
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }

/* 图片画廊 */
.images-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}
.gallery-item {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  animation: pop-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.gallery-item img {
  width: 100%;
  display: block;
  cursor: pointer;
  transition: transform 0.4s ease;
}
.gallery-item:hover img { transform: scale(1.02); }
.gallery-overlay {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 20px;
  background: linear-gradient(transparent, rgba(0,0,0,0.5));
  display: flex;
  justify-content: flex-end;
  opacity: 0;
  transition: opacity 0.3s;
}
.gallery-item:hover .gallery-overlay { opacity: 1; }
.dl-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.9);
  border: none;
  border-radius: 20px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: background 0.2s;
}
.dl-btn:hover { background: #fff; }

/* 创作区 */
.creator {
  position: relative;
  z-index: 1;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 28px;
  border: 1px solid rgba(255,255,255,0.8);
  box-shadow: 0 8px 32px rgba(0,0,0,0.06);
}

.prompt-wrap {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 20px;
}

.prompt-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
  background: transparent;
  font-family: inherit;
}
.prompt-input::placeholder { color: #bbb; }

.gen-btn {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 20px;
  border: none;
  background: linear-gradient(135deg, #6366f1, #ec4899);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
}
.gen-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.5);
}
.gen-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-loading {
  width: 20px; height: 20px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.options-row {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 模板标签 */
.templates {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tpl-tag {
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(0,0,0,0.04);
  color: #666;
  border: 1px solid transparent;
}
.tpl-tag:hover { background: rgba(99,102,241,0.08); color: #6366f1; border-color: rgba(99,102,241,0.2); }
.tpl-tag.active {
  background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(236,72,153,0.15));
  color: #6366f1;
  border-color: rgba(99,102,241,0.3);
}

/* 控制项 */
.controls {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.ctrl-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ctrl-label {
  font-size: 12px;
  color: #999;
}
.ctrl-btns {
  display: flex;
  gap: 4px;
}
.ctrl-btn {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #fff;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.15s;
}
.ctrl-btn:hover { border-color: #6366f1; color: #6366f1; }
.ctrl-btn.active {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

/* 动画 */
.slide-up-enter-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(20px); }
.slide-up-leave-to { opacity: 0; transform: translateY(-10px); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -20px) scale(1.05); }
  66% { transform: translate(-10px, 10px) scale(0.95); }
}
@keyframes blink {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}
@keyframes pop-in {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}
</style>
