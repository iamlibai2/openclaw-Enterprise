<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>帮助文档</h1>
      <p>OpenClaw 使用指南和 API 文档</p>
    </el-card>

    <el-card class="content-card">
      <el-collapse v-model="activeDocs">
        <el-collapse-item title="快速开始" name="quickstart">
          <div class="doc-content">
            <h3>安装与配置</h3>
            <p>1. 克隆仓库并安装依赖：</p>
            <pre class="code-block">git clone https://github.com/openclaw/openclaw
cd openclaw && npm install</pre>
            <p>2. 启动 Gateway：</p>
            <pre class="code-block">openclaw gateway start</pre>
          </div>
        </el-collapse-item>

        <el-collapse-item title="Agent 配置" name="agent">
          <div class="doc-content">
            <h3>创建 Agent</h3>
            <p>在 <code>~/.openclaw/agents/</code> 目录下创建配置文件：</p>
            <pre class="code-block">name: my-agent
model: bailian/glm-5
skills:
  - feishu
  - weather</pre>
          </div>
        </el-collapse-item>

        <el-collapse-item title="工具说明" name="tools">
          <div class="doc-content">
            <h3>内置工具</h3>
            <ul>
              <li><strong>read/write/edit</strong> - 文件操作</li>
              <li><strong>exec</strong> - 执行命令</li>
              <li><strong>web_search/web_fetch</strong> - 网络搜索</li>
              <li><strong>message</strong> - 发送消息</li>
              <li><strong>feishu_*</strong> - 飞书工具集</li>
            </ul>
          </div>
        </el-collapse-item>

        <el-collapse-item title="API 文档" name="api">
          <div class="doc-content">
            <h3>HTTP API</h3>
            <p>Gateway 提供以下 API：</p>
            <ul>
              <li><code>GET /api/gateway/status</code> - 获取运行状态</li>
              <li><code>POST /api/gateway/restart</code> - 重启 Gateway</li>
              <li><code>GET /api/sessions/list</code> - 获取会话列表</li>
            </ul>
          </div>
        </el-collapse-item>
      </el-collapse>

      <div class="doc-links">
        <el-link href="https://docs.openclaw.ai" target="_blank" type="primary">
          完整文档 → docs.openclaw.ai
        </el-link>
        <el-link href="https://github.com/openclaw/openclaw" target="_blank" type="primary">
          GitHub 仓库
        </el-link>
        <el-link href="https://discord.com/invite/clawd" target="_blank" type="primary">
          Discord 社区
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeDocs = ref(['quickstart'])
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
}

.content-card {
  min-height: 500px;
}

.doc-content {
  padding: 16px;
  color: #606266;
}

.doc-content h3 {
  margin-bottom: 12px;
  color: #303133;
}

.doc-content ul {
  margin-left: 20px;
}

.doc-content li {
  margin-bottom: 8px;
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  margin: 8px 0;
}

.doc-links {
  margin-top: 24px;
  display: flex;
  gap: 16px;
}
</style>