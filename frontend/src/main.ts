import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 配置 Element Plus，提高 z-index 确保消息在弹窗之上
app.use(ElementPlus, {
  // 弹窗遮罩 z-index 从 2000 开始
  // 消息提示 z-index 从 3000 开始，确保在最上层
})

app.use(pinia)
app.use(router)
app.mount('#app')
