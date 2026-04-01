<template>
  <div class="dashboard-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h1>OpenClaw 团队工作台</h1>
        <p class="header-date">今天是 {{ todayDate }} ｜ 团队已稳定运行 {{ uptime }}</p>
      </div>
      <div class="header-actions">
        <el-button @click="generateDemoData" :loading="generatingDemo" v-if="showDemoButton">
          <el-icon><MagicStick /></el-icon>
          生成演示数据
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card" v-for="stat in stats" :key="stat.key">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-sub" :class="stat.subClass">
          <el-icon v-if="stat.icon"><component :is="stat.icon" /></el-icon>
          {{ stat.subText }}
        </div>
      </div>
    </div>

    <!-- 工作趋势图 -->
    <div class="trend-section">
      <div class="section-header">
        <h3>本周工作趋势</h3>
      </div>
      <div class="chart-container" ref="trendChartRef"></div>
      <div class="trend-summary">
        <span>本周累计：{{ trendTotal }}项任务</span>
        <span class="trend-change" :class="trendChangeClass">
          较上周 {{ trendChange >= 0 ? '↑' : '↓' }}{{ Math.abs(trendChange) }}%
        </span>
        <span class="trend-status">{{ trendStatus }}</span>
      </div>
    </div>

    <!-- 双栏布局：员工排行 + 任务类型分布 -->
    <div class="dual-section">
      <!-- 员工绩效排行 -->
      <div class="ranking-section">
        <div class="section-header">
          <h3>员工绩效排行</h3>
          <el-button text type="primary" size="small">查看全部 →</el-button>
        </div>
        <div class="ranking-list">
          <div class="ranking-item" v-for="(item, index) in rankings" :key="item.agentId">
            <div class="rank-badge">
              <span v-if="index === 0">🥇</span>
              <span v-else-if="index === 1">🥈</span>
              <span v-else-if="index === 2">🥉</span>
              <span v-else class="rank-number">{{ index + 1 }}</span>
            </div>
            <div class="rank-info">
              <span class="rank-name">{{ item.agentName }}</span>
              <span class="rank-stats">{{ item.taskCount }}项 {{ item.successRate }}%</span>
            </div>
            <div class="rank-progress">
              <el-progress
                :percentage="item.successRate"
                :stroke-width="8"
                :color="getProgressColor(item.successRate)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 任务类型分布 -->
      <div class="distribution-section">
        <div class="section-header">
          <h3>任务类型分布</h3>
        </div>
        <div class="distribution-list">
          <div class="distribution-item" v-for="item in distributions" :key="item.type">
            <div class="dist-icon">{{ item.icon }}</div>
            <div class="dist-info">
              <span class="dist-name">{{ item.type }}</span>
              <el-progress
                :percentage="item.percent"
                :stroke-width="12"
                :color="getDistColor(item.type)"
              />
            </div>
            <div class="dist-value">{{ item.percent }}%</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近完成的工作 -->
    <div class="recent-section">
      <div class="section-header">
        <h3>最近完成的工作</h3>
        <el-button text type="primary" size="small">查看全部 →</el-button>
      </div>
      <div class="recent-list">
        <div class="recent-item" v-for="task in recentTasks" :key="task.id">
          <div class="task-status">
            <span v-if="task.status === 'completed'">✅</span>
            <span v-else-if="task.status === 'running'">⏳</span>
            <span v-else>❌</span>
          </div>
          <div class="task-agent">{{ task.agentName }}</div>
          <div class="task-time">{{ formatTime(task.createdAt) }}</div>
          <div class="task-title">{{ task.title }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { taskApi, type TaskOverview, type TaskRanking, type TaskTypeDistribution, type TaskRecent } from '../api'
import * as echarts from 'echarts'

const trendChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

const loading = ref(false)
const generatingDemo = ref(false)

// 概览数据
const overview = ref<TaskOverview>({
  todayTotal: 0,
  todayChange: 0,
  completionRate: 0,
  avgDuration: 0,
  inProgress: 0
})

// 趋势数据
const trendLabels = ref<string[]>([])
const trendValues = ref<number[]>([])
const trendTotal = ref(0)
const trendChange = ref(0)

// 排行数据
const rankings = ref<TaskRanking[]>([])

// 分布数据
const distributions = ref<TaskTypeDistribution[]>([])

// 最近任务
const recentTasks = ref<TaskRecent[]>([])

// 是否显示演示按钮（当没有数据时）
const showDemoButton = computed(() => overview.value.todayTotal === 0)

// 今日日期
const todayDate = computed(() => {
  const now = new Date()
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]}`
})

// 运行时长（模拟）
const uptime = computed(() => {
  return '3天12小时'
})

// 统计卡片
const stats = computed(() => [
  {
    key: 'todayTotal',
    value: overview.value.todayTotal + '项',
    label: '今日任务',
    subText: overview.value.todayChange >= 0 ? `↑${overview.value.todayChange}%` : `↓${Math.abs(overview.value.todayChange)}%`,
    subClass: overview.value.todayChange >= 0 ? 'up' : 'down',
    icon: overview.value.todayChange >= 0 ? ArrowUp : ArrowDown
  },
  {
    key: 'completionRate',
    value: overview.value.completionRate + '%',
    label: '完成率',
    subText: getRateLabel(overview.value.completionRate),
    subClass: getRateClass(overview.value.completionRate)
  },
  {
    key: 'avgDuration',
    value: formatDuration(overview.value.avgDuration),
    label: '平均耗时',
    subText: overview.value.avgDuration < 180 ? '快' : overview.value.avgDuration < 300 ? '中' : '慢',
    subClass: overview.value.avgDuration < 180 ? 'fast' : overview.value.avgDuration < 300 ? 'normal' : 'slow'
  },
  {
    key: 'inProgress',
    value: overview.value.inProgress + '项',
    label: '进行中',
    subText: '处理中',
    subClass: 'running'
  }
])

// 趋势变化样式
const trendChangeClass = computed(() => trendChange.value >= 0 ? 'up' : 'down')

// 趋势状态文本
const trendStatus = computed(() => {
  if (trendChange.value > 10) return '📈 团队状态良好'
  if (trendChange.value > 0) return '➡️ 稳步发展'
  if (trendChange.value === 0) return '➡️ 保持平稳'
  return '📉 需要关注'
})

function getRateLabel(rate: number): string {
  if (rate >= 95) return '优秀'
  if (rate >= 85) return '良好'
  if (rate >= 70) return '一般'
  return '需关注'
}

function getRateClass(rate: number): string {
  if (rate >= 95) return 'excellent'
  if (rate >= 85) return 'good'
  if (rate >= 70) return 'normal'
  return 'warning'
}

function getProgressColor(rate: number): string {
  if (rate >= 95) return '#52c41a'
  if (rate >= 85) return '#1890ff'
  if (rate >= 70) return '#faad14'
  return '#ff4d4f'
}

function getDistColor(type: string): string {
  const colors: Record<string, string> = {
    '报告生成': '#1890ff',
    '文档撰写': '#52c41a',
    '代码开发': '#722ed1',
    '数据分析': '#fa8c16',
    '内容创作': '#eb2f96',
    '翻译': '#13c2c2',
    '邮件处理': '#2f54eb',
    '其他': '#8c8c8c'
  }
  return colors[type] || '#1890ff'
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}分`
}

function formatTime(time: string): string {
  if (!time) return '-'
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

async function loadDashboardData() {
  loading.value = true
  try {
    // 加载概览数据
    const overviewRes = await taskApi.overview()
    if (overviewRes.data.success) {
      overview.value = overviewRes.data.data
    }

    // 加载趋势数据
    const trendRes = await taskApi.trend(7)
    if (trendRes.data.success) {
      trendLabels.value = trendRes.data.data.labels
      trendValues.value = trendRes.data.data.values
      trendTotal.value = trendRes.data.data.total
      trendChange.value = trendRes.data.data.change
      renderTrendChart()
    }

    // 加载排行数据
    const rankingRes = await taskApi.ranking(7, 5)
    if (rankingRes.data.success) {
      rankings.value = rankingRes.data.data
    }

    // 加载分布数据
    const distRes = await taskApi.typeDistribution(7)
    if (distRes.data.success) {
      distributions.value = distRes.data.data
    }

    // 加载最近任务
    const recentRes = await taskApi.recent(10)
    if (recentRes.data.success) {
      recentTasks.value = recentRes.data.data
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function renderTrendChart() {
  if (!trendChartRef.value) return

  if (trendChart) {
    trendChart.dispose()
  }

  trendChart = echarts.init(trendChartRef.value)

  const option = {
    grid: {
      left: '40',
      right: '20',
      top: '20',
      bottom: '40'
    },
    xAxis: {
      type: 'category',
      data: trendLabels.value,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#666', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#666', fontSize: 12 },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: [{
      type: 'line',
      data: trendValues.value,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: {
        color: '#1890ff',
        width: 3
      },
      itemStyle: {
        color: '#1890ff',
        borderColor: '#fff',
        borderWidth: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
            { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
          ]
        }
      }
    }]
  }

  trendChart.setOption(option)
}

async function generateDemoData() {
  generatingDemo.value = true
  try {
    const res = await taskApi.generateDemo()
    if (res.data.success) {
      ElMessage.success('演示数据已生成')
      await loadDashboardData()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e: any) {
    ElMessage.error('生成失败：' + e.message)
  } finally {
    generatingDemo.value = false
  }
}

onMounted(() => {
  loadDashboardData()

  // 监听窗口变化，调整图表大小
  window.addEventListener('resize', () => {
    trendChart?.resize()
  })
})
</script>

<style scoped>
.dashboard-page {
  min-height: calc(100vh - 96px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-info h1 {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.header-date {
  font-size: 14px;
  color: #909399;
}

/* 统计卡片 */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  border: 1px solid #ebeef5;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-sub {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-sub.up { color: #52c41a; }
.stat-sub.down { color: #ff4d4f; }
.stat-sub.excellent { color: #52c41a; }
.stat-sub.good { color: #1890ff; }
.stat-sub.normal { color: #faad14; }
.stat-sub.warning { color: #ff4d4f; }
.stat-sub.fast { color: #52c41a; }
.stat-sub.normal { color: #faad14; }
.stat-sub.slow { color: #ff4d4f; }
.stat-sub.running { color: #1890ff; }

/* 趋势图 */
.trend-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  height: 200px;
}

.trend-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #606266;
  margin-top: 16px;
}

.trend-change.up { color: #52c41a; }
.trend-change.down { color: #ff4d4f; }

.trend-status {
  color: #52c41a;
}

/* 双栏布局 */
.dual-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.ranking-section,
.distribution-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rank-badge {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rank-badge span {
  font-size: 18px;
}

.rank-number {
  font-size: 14px;
  font-weight: 600;
  color: #909399;
}

.rank-info {
  flex: 1;
  min-width: 0;
}

.rank-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.rank-stats {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.rank-progress {
  width: 120px;
}

/* 分布列表 */
.distribution-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.distribution-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dist-icon {
  font-size: 18px;
}

.dist-info {
  flex: 1;
  min-width: 0;
}

.dist-name {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
  display: block;
}

.dist-value {
  font-size: 14px;
  color: #606266;
  width: 50px;
  text-align: right;
}

/* 最近任务 */
.recent-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.recent-list {
  display: flex;
  flex-direction: column;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.recent-item:last-child {
  border-bottom: none;
}

.task-status {
  font-size: 16px;
}

.task-agent {
  font-size: 14px;
  color: #1890ff;
  min-width: 80px;
}

.task-time {
  font-size: 12px;
  color: #909399;
  min-width: 80px;
}

.task-title {
  font-size: 14px;
  color: #303133;
  flex: 1;
}
</style>