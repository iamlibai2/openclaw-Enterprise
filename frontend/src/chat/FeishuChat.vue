<template>
  <div class="feishu-chat">
    <!-- 会话列表 -->
    <div class="conversation-panel">
      <div class="panel-header">
        <div class="panel-title">消息</div>
        <div class="panel-actions">
          <button class="action-btn" @click="goToMoments" title="朋友圈">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <circle cx="12" cy="12" r="10"></circle>
              <circle cx="12" cy="12" r="4"></circle>
              <line x1="21.17" y1="8" x2="12" y2="8"></line>
              <line x1="3.95" y1="6.06" x2="8.54" y2="14"></line>
              <line x1="10.88" y1="21.94" x2="15.46" y2="14"></line>
            </svg>
          </button>
          <button class="action-btn" @click="showCreateGroup = true" title="创建群聊">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>
      </div>

      <div class="search-box">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input v-model="searchQuery" type="text" placeholder="搜索" />
      </div>

      <div class="conversation-list">
        <div
          v-for="conv in allConversations"
          :key="conv.key"
          :class="['conversation-item', { active: selectedId === conv.id && currentType === conv.type }]"
          @click="selectConversation(conv.type, conv.id)"
        >
          <div v-if="conv.type === 'single'" class="conv-avatar" :style="getAvatarStyle(conv.id)">
            {{ conv.name?.charAt(0) || '?' }}
          </div>
          <div v-else class="conv-avatar group">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </div>
          <div class="conv-info">
            <div class="conv-name">
              <span class="name-text">{{ conv.name }}</span>
              <span v-if="conv.type === 'group'" class="group-tag">群聊</span>
            </div>
            <div class="conv-preview">{{ conv.lastMessage || (conv.type === 'group' ? `${conv.memberCount} 人` : '开始聊天吧') }}</div>
          </div>
          <div class="conv-meta">
            <span class="conv-time" v-if="conv.lastTime">{{ formatShortTime(conv.lastTime) }}</span>
            <span class="conv-unread" v-if="conv.unread">{{ conv.unread }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 聊天主区域 -->
    <div class="chat-main">
      <template v-if="currentConversation">
        <!-- 顶部栏 -->
        <div class="chat-header">
          <div class="header-left">
            <div class="header-avatar" v-if="currentType === 'single'" :style="getAvatarStyle(currentAgent?.id)">
              {{ currentAgent?.name?.charAt(0) || '?' }}
            </div>
            <div class="header-avatar group" v-else>
              <span>#</span>
            </div>
            <div class="header-info">
              <div class="header-name">{{ currentTitle }}</div>
              <div class="header-desc" v-if="currentType === 'group' && currentGroup">
                {{ currentGroup.participants.map(p => p.name).join('、') }}
              </div>
            </div>
          </div>
          <div class="header-right">
            <button class="header-btn" @click="showSessionsHistory = true" title="对话历史">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
            <button class="header-btn" @click="showMemory = true" title="记忆">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
              </svg>
            </button>
            <button class="header-btn" @click="showFilesPanel = !showFilesPanel" title="文件">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
            <button class="header-btn" @click="showDetail = !showDetail" title="信息">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            </button>
          </div>
        </div>

        <!-- 消息区域 -->
        <div class="messages-area" ref="messagesRef">
          <!-- 空状态欢迎 -->
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-avatar" :style="currentType === 'single' ? getAvatarStyle(currentAgent?.id) : {}">
              <template v-if="currentType === 'single'">{{ currentAgent?.name?.charAt(0) }}</template>
              <template v-else>#</template>
            </div>
            <div class="welcome-title">{{ currentTitle }}</div>
            <div class="welcome-desc" v-if="currentType === 'single'">
              这是与 {{ currentAgent?.name }} 的对话，发送消息开始聊天
            </div>
            <div class="welcome-desc" v-else>
              这是群聊，主持人会协调各 Agent 参与讨论
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-for="(msg, idx) in messages" :key="msg.id" :class="['message-row', msg.role]">
            <div class="msg-avatar" :style="getAvatarStyle(msg.sourceAgent || currentAgent?.id)">
              {{ getSenderName(msg)?.charAt(0) || '?' }}
            </div>
            <div class="msg-bubble">
              <div v-if="msg.role === 'assistant'" class="msg-header">
                <span class="msg-sender">{{ getSenderName(msg) }}</span>
              </div>
              <div class="msg-text" v-html="renderMarkdown(getMessageText(msg))"></div>
              <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>

          <!-- Reading Indicator：Agent 已收到消息，正在思考 -->
          <div v-if="isStreaming && !streamContent" class="message-row assistant reading">
            <div class="msg-avatar" :style="getAvatarStyle(currentAgent?.id)">
              {{ currentAgent?.name?.charAt(0) || '?' }}
            </div>
            <div class="msg-bubble">
              <div class="msg-header">
                <span class="msg-sender">{{ currentAgent?.name }}</span>
              </div>
              <div class="reading-indicator">
                <span class="reading-dots">
                  <i></i><i></i><i></i>
                </span>
              </div>
            </div>
          </div>

          <!-- Streaming：Agent 正在输出内容 -->
          <div v-if="isStreaming && streamContent" class="message-row assistant streaming">
            <div class="msg-avatar" :style="getAvatarStyle(currentAgent?.id)">
              {{ currentAgent?.name?.charAt(0) || '?' }}
            </div>
            <div class="msg-bubble">
              <div class="msg-header">
                <span class="msg-sender">{{ currentAgent?.name }}</span>
                <span class="msg-time typing">
                  <span class="typing-dots"><i></i><i></i><i></i></span>
                </span>
              </div>
              <div class="msg-text" v-html="renderMarkdown(streamContent)"></div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-box">
            <div class="input-tools">
              <button class="tool-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
              </button>
              <button class="tool-btn">
                <span style="font-size: 18px;">😊</span>
              </button>
            </div>
            <textarea
              ref="textareaRef"
              v-model="inputMessage"
              placeholder="发送消息..."
              rows="1"
              @keydown="handleKeydown"
              @input="autoResize"
            ></textarea>
            <button class="send-btn" :class="{ active: canSend }" @click="sendMessage">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-chat">
        <div class="empty-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <div class="empty-title">开始对话</div>
        <div class="empty-desc">选择左侧的联系人或群聊开始聊天</div>
      </div>
    </div>

    <!-- 右侧详情面板 -->
    <Transition name="slide-left">
      <div v-if="showDetail && (currentGroup || currentAgent)" class="detail-panel">
        <div class="detail-header">
          <span>{{ currentGroup ? '群聊信息' : 'Agent 信息' }}</span>
          <button class="close-btn" @click="showDetail = false">×</button>
        </div>
        <div class="detail-body" v-if="currentGroup">
          <div class="detail-section">
            <div class="section-title">主持人</div>
            <div class="member-item">
              <div class="member-avatar" :style="getAvatarStyle(currentGroup.hostAgentId)">
                {{ currentGroup.hostAgentName?.charAt(0) }}
              </div>
              <div class="member-name">{{ currentGroup.hostAgentName }}</div>
              <span class="member-tag">主持人</span>
            </div>
          </div>
          <div class="detail-section">
            <div class="section-title">参与者 · {{ currentGroup.participants.length }}</div>
            <div v-for="p in currentGroup.participants" :key="p.agentId" class="member-item">
              <div class="member-avatar" :style="getAvatarStyle(p.agentId)">
                {{ p.name?.charAt(0) }}
              </div>
              <div class="member-name">{{ p.name }}</div>
            </div>
          </div>
        </div>
        <div class="detail-body" v-else-if="currentAgent">
          <div class="detail-section">
            <div class="section-title">基本信息</div>
            <div class="info-row">
              <span class="info-label">名称</span>
              <span class="info-value">{{ currentAgent.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">ID</span>
              <span class="info-value mono">{{ currentAgent.id }}</span>
            </div>
            <div class="info-row" v-if="currentAgent.model">
              <span class="info-label">模型</span>
              <span class="info-value">{{ currentAgent.model }}</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 文件面板 -->
    <Transition name="slide-left">
      <div v-if="showFilesPanel" class="files-panel">
        <div class="panel-header">
          <span>会话文件</span>
          <button class="close-btn" @click="showFilesPanel = false">×</button>
        </div>
        <div class="panel-content">
          <div v-if="filesLoading" class="files-loading">
            <span class="loading-spinner"></span>
            <span>加载中...</span>
          </div>
          <div v-else-if="filesError" class="files-error">
            {{ filesError }}
          </div>
          <div v-else-if="agentFiles.length === 0" class="files-empty">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <p>暂无文件</p>
          </div>
          <div v-else class="files-list">
            <div
              v-for="file in agentFiles"
              :key="file.name"
              class="file-item"
              @click="handleFileClick(file)"
            >
              <div class="file-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <div class="file-info">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-meta">
                  <span v-if="file.size">{{ formatFileSize(file.size) }}</span>
                  <span v-if="file.createdAt">{{ formatFileDate(file.createdAt) }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="panel-footer">
          <button class="refresh-btn" @click="loadAgentFiles" :disabled="filesLoading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            刷新
          </button>
        </div>
      </div>
    </Transition>

    <!-- 弹窗 -->
    <div v-if="showCreateGroup" class="modal-overlay" @click.self="showCreateGroup = false">
      <div class="modal">
        <div class="modal-header">
          <span>创建群聊</span>
          <button class="close-btn" @click="showCreateGroup = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <label>群聊名称</label>
            <input v-model="newGroupName" type="text" placeholder="输入群聊名称" />
          </div>
          <div class="form-item">
            <label>选择主持人</label>
            <div class="agent-select">
              <div
                v-for="agent in agents"
                :key="agent.id"
                :class="['agent-option', { selected: newGroupHost === agent.id }]"
                @click="newGroupHost = agent.id"
              >
                <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                  {{ agent.name?.charAt(0) }}
                </div>
                <span>{{ agent.name }}</span>
              </div>
            </div>
          </div>
          <div class="form-item">
            <label>选择参与者</label>
            <div class="agent-select multi">
              <div
                v-for="agent in agents.filter(a => a.id !== newGroupHost)"
                :key="agent.id"
                :class="['agent-option', { selected: newGroupParticipants.includes(agent.id) }]"
                @click="toggleParticipant(agent.id)"
              >
                <div class="agent-avatar" :style="getAvatarStyle(agent.id)">
                  {{ agent.name?.charAt(0) }}
                </div>
                <span>{{ agent.name }}</span>
                <div v-if="newGroupParticipants.includes(agent.id)" class="check">✓</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showCreateGroup = false">取消</button>
          <button class="btn-confirm" :disabled="!canCreateGroup" @click="createGroup">创建</button>
        </div>
      </div>
    </div>

    <!-- 朋友圈弹窗 -->
    <div v-if="showMoments" class="modal-overlay" @click.self="showMoments = false">
      <div class="moments-modal">
        <div class="moments-modal-header">
          <span>Agent 朋友圈</span>
          <button class="close-btn" @click="showMoments = false">×</button>
        </div>
        <div class="moments-modal-body">
          <div v-if="momentsLoading" class="moments-loading">
            加载中...
          </div>
          <div v-else-if="moments.length === 0" class="moments-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <p>暂无动态</p>
          </div>
          <div v-else class="moments-list">
            <div v-for="moment in moments" :key="moment.id" class="moment-item">
              <div class="moment-head">
                <div class="moment-avatar" :style="getAvatarStyle(moment.agent_id)">
                  {{ moment.agent_name?.charAt(0) || 'A' }}
                </div>
                <div class="moment-info">
                  <span class="moment-name">{{ moment.agent_name || moment.agent_id }}</span>
                  <span class="moment-time">{{ formatMomentTime(moment.created_at) }}</span>
                </div>
                <span v-if="moment.moment_type" class="moment-tag">{{ getMomentTypeLabel(moment.moment_type) }}</span>
              </div>
              <div class="moment-content">{{ moment.content }}</div>
              <div v-if="moment.image_url" class="moment-img">
                <img :src="moment.image_url" alt="" />
              </div>
              <div class="moment-actions">
                <button class="moment-action-btn" :class="{ liked: moment.isLiked }" @click="handleMomentLike(moment)">
                  <svg width="16" height="16" viewBox="0 0 24 24" :fill="moment.isLiked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                  </svg>
                  {{ moment.like_count || 0 }}
                </button>
                <button class="moment-action-btn" @click="toggleMomentComment(moment)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                  {{ moment.comments?.length || 0 }}
                </button>
              </div>
              <div v-if="moment.comments?.length" class="moment-comments">
                <div v-for="c in moment.comments" :key="c.id" class="comment-line">
                  <span class="comment-author">{{ c.user_name || c.agent_name }}:</span>
                  <span>{{ c.content }}</span>
                </div>
              </div>
              <div v-if="moment.showCommentInput" class="comment-input-row">
                <input v-model="moment.newComment" placeholder="写评论..." @keyup.enter="submitMomentComment(moment)" />
                <button @click="submitMomentComment(moment)">发送</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 对话历史弹窗 -->
    <div v-if="showSessionsHistory" class="modal-overlay" @click.self="showSessionsHistory = false">
      <div class="history-modal">
        <div class="history-modal-header">
          <span>{{ currentAgent?.name || 'Agent' }} - 对话历史</span>
          <button class="close-btn" @click="showSessionsHistory = false">×</button>
        </div>
        <div class="history-modal-body">
          <!-- 会话列表 -->
          <div class="history-main">
            <div v-if="sessionsLoading" class="history-loading">加载中...</div>
            <div v-else-if="sessionsList.length === 0" class="history-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <p>暂无对话记录</p>
            </div>
            <div v-else class="sessions-grid">
              <div
                v-for="session in sessionsList"
                :key="session.sessionId"
                :class="['session-card', { active: selectedSession?.sessionId === session.sessionId, reset: session.isReset }]"
                @click="selectSessionRecord(session)"
              >
                <div class="session-card-header">
                  <span class="session-channel">{{ session.channel }}</span>
                  <span :class="['session-status', session.status]">{{ session.isReset ? '归档' : session.status }}</span>
                </div>
                <div class="session-card-time">{{ session.updatedAt }}</div>
                <div class="session-card-model" v-if="session.model">{{ session.model }}</div>
              </div>
            </div>
          </div>
          <!-- 消息详情 -->
          <div class="history-detail" v-if="selectedSession">
            <div class="detail-title">
              <span>对话详情</span>
              <span class="detail-time">{{ selectedSession.updatedAt }}</span>
            </div>
            <div class="detail-messages" v-if="sessionMessages.length > 0">
              <div v-for="msg in sessionMessages" :key="msg.id" :class="['detail-msg', msg.role]">
                <div class="msg-role">{{ msg.role === 'user' ? '用户' : currentAgent?.name || 'AI' }}</div>
                <div class="msg-content" v-html="renderMarkdown(msg.text)"></div>
              </div>
            </div>
            <div v-else class="detail-empty">加载中...</div>
          </div>
          <div class="history-detail history-detail-empty" v-else>
            <div class="detail-empty">选择会话查看详情</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 记忆弹窗 -->
    <div v-if="showMemory" class="modal-overlay" @click.self="showMemory = false">
      <div class="memory-modal">
        <div class="memory-modal-header">
          <span>{{ currentAgent?.name || 'Agent' }} - 记忆</span>
          <button class="close-btn" @click="showMemory = false">×</button>
        </div>
        <div class="memory-modal-body">
          <!-- 记忆文件列表 -->
          <div class="memory-main">
            <div v-if="memoryLoading" class="memory-loading">加载中...</div>
            <div v-else-if="memoryFiles.length === 0" class="memory-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
              </svg>
              <p>暂无记忆文件</p>
            </div>
            <div v-else class="memory-files">
              <div
                v-for="file in memoryFiles"
                :key="file.date"
                :class="['memory-file', { active: selectedMemoryFile?.date === file.date }]"
                @click="selectMemoryFile(file)"
              >
                <div class="file-icon">📝</div>
                <div class="file-info">
                  <div class="file-date">{{ file.date }}</div>
                  <div class="file-size">{{ formatSize(file.size) }}</div>
                </div>
              </div>
            </div>
          </div>
          <!-- 记忆内容 -->
          <div class="memory-content-panel" v-if="selectedMemoryFile">
            <div class="content-title">{{ selectedMemoryFile.date }}</div>
            <div class="content-body" v-if="memoryContent" v-html="renderMarkdown(memoryContent)"></div>
            <div v-else class="content-loading">加载中...</div>
          </div>
          <div class="memory-content-panel memory-content-empty" v-else>
            <div class="content-loading">选择文件查看内容</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../user/stores'
import { agentApi, chatApi, momentApi, sessionApi, memoryApi, AgentMoment } from '../api'
import { createGatewayClient, getGatewayClient, extractText } from '../utils/gateway-ws'
import { renderMessageContent } from '../utils/markdown'
import type { Agent, Message, Participant } from '../chat/types'

// ==================== Types ====================

interface GroupChat {
  id: string
  name: string
  hostAgentId: string
  hostAgentName: string
  participants: Participant[]
  lastMessage?: string
  lastTime?: number
}

interface AgentConv {
  id: string
  name: string
  lastMessage?: string
  lastTime?: number
  unread?: number
}

// ==================== State ====================

const userStore = useUserStore()
const agents = ref<Agent[]>([])
const agentConvs = ref<AgentConv[]>([])
const groups = ref<GroupChat[]>([])

const searchQuery = ref('')
const currentType = ref<'single' | 'group' | null>(null)
const selectedId = ref<string>('')
const showDetail = ref(false)
const showCreateGroup = ref(false)
const showFilesPanel = ref(false)
const showMoments = ref(false)
const showSessionsHistory = ref(false)
const showMemory = ref(false)

const messagesMap = ref<Map<string, Message[]>>(new Map())
const messages = ref<Message[]>([])

// 按会话隔离的 streaming 状态
const streamingMap = ref<Map<string, boolean>>(new Map())
const streamContentMap = ref<Map<string, string>>(new Map())

// 当前会话的 streaming 状态（computed）
const currentStreamKey = computed(() => {
  return currentType.value === 'single' ? `single-${selectedId.value}` : `group-${selectedId.value}`
})
const isStreaming = computed(() => !!streamingMap.value.get(currentStreamKey.value))
const streamContent = computed(() => streamContentMap.value.get(currentStreamKey.value) || '')

const inputMessage = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messagesRef = ref<HTMLElement | null>(null)

const newGroupName = ref('')
const newGroupHost = ref('')
const newGroupParticipants = ref<string[]>([])

// Gateway 客户端
let client: ReturnType<typeof createGatewayClient> | null = null
const sessionMap = ref<Map<string, string>>(new Map())

// ==================== 文件面板状态 ====================

const filesLoading = ref(false)
const filesError = ref<string | null>(null)

interface ArtifactFile {
  name: string
  path: string
  size?: number
  createdAt?: number
  toolName?: string
}
const agentFiles = ref<ArtifactFile[]>([])

// ==================== Computed ====================

const unreadCount = computed(() => agentConvs.value.reduce((acc, c) => acc + (c.unread || 0), 0))

const filteredAgents = computed(() => {
  if (!searchQuery.value) return agentConvs.value
  const q = searchQuery.value.toLowerCase()
  return agentConvs.value.filter(a => a.name.toLowerCase().includes(q))
})

const filteredGroups = computed(() => {
  if (!searchQuery.value) return groups.value
  const q = searchQuery.value.toLowerCase()
  return groups.value.filter(g => g.name.toLowerCase().includes(q))
})

// 合并所有会话，按时间排序
const allConversations = computed(() => {
  const q = searchQuery.value.toLowerCase()
  const list: Array<{
    key: string
    id: string
    type: 'single' | 'group'
    name: string
    lastMessage?: string
    lastTime?: number
    unread?: number
    memberCount?: number
  }> = []

  // 添加私聊
  for (const a of agentConvs.value) {
    if (q && !a.name.toLowerCase().includes(q)) continue
    list.push({
      key: `single-${a.id}`,
      id: a.id,
      type: 'single',
      name: a.name,
      lastMessage: a.lastMessage,
      lastTime: a.lastTime,
      unread: a.unread
    })
  }

  // 添加群聊
  for (const g of groups.value) {
    if (q && !g.name.toLowerCase().includes(q)) continue
    list.push({
      key: `group-${g.id}`,
      id: g.id,
      type: 'group',
      name: g.name,
      lastMessage: g.lastMessage,
      lastTime: g.lastTime,
      memberCount: g.participants.length
    })
  }

  // 按时间排序，有消息的排前面
  return list.sort((a, b) => {
    if (!a.lastTime && !b.lastTime) return 0
    if (!a.lastTime) return 1
    if (!b.lastTime) return -1
    return b.lastTime - a.lastTime
  })
})

const currentAgent = computed(() => agents.value.find(a => a.id === selectedId.value))
const currentGroup = computed(() => groups.value.find(g => g.id === selectedId.value))
const currentConversation = computed(() => currentType.value !== null)
const currentTitle = computed(() => {
  if (currentType.value === 'single') return currentAgent.value?.name || '对话'
  if (currentType.value === 'group') return currentGroup.value?.name || '群聊'
  return ''
})

const canSend = computed(() => inputMessage.value.trim() && !isStreaming.value)
const canCreateGroup = computed(() => newGroupHost.value && newGroupParticipants.value.length > 0)

// ==================== Colors ====================

const avatarColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
  'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
]

function getAvatarStyle(id?: string): Record<string, string> {
  if (!id) return { background: avatarColors[0] }
  const hash = id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return { background: avatarColors[hash % avatarColors.length] }
}

// ==================== Methods ====================

function goToMoments() {
  showMoments.value = true
  loadMoments()
}

// ==================== 朋友圈 ====================

const momentsLoading = ref(false)
const moments = ref<(AgentMoment & { isLiked?: boolean; showCommentInput?: boolean; newComment?: string })[]>([])

async function loadMoments() {
  momentsLoading.value = true
  try {
    const res = await momentApi.list({ page: 1, limit: 20 })
    if (res.data.success) {
      const userId = userStore.user?.id
      moments.value = res.data.data.map(m => ({
        ...m,
        isLiked: userId ? m.likes.includes(userId) : false,
        showCommentInput: false,
        newComment: ''
      }))
    }
  } catch (e) {
    console.error('Load moments failed:', e)
  } finally {
    momentsLoading.value = false
  }
}

function formatMomentTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function getMomentTypeLabel(type: string): string {
  const labels: Record<string, string> = { work: '工作', life: '生活', achievement: '成就' }
  return labels[type] || type
}

async function handleMomentLike(moment: any) {
  try {
    const res = await momentApi.like(moment.id)
    if (res.data.success) {
      moment.isLiked = res.data.data.liked
      moment.like_count = res.data.data.like_count
    }
  } catch (e) {
    console.error('Like failed:', e)
  }
}

function toggleMomentComment(moment: any) {
  moment.showCommentInput = !moment.showCommentInput
}

async function submitMomentComment(moment: any) {
  if (!moment.newComment?.trim()) return
  try {
    const res = await momentApi.comment(moment.id, moment.newComment.trim())
    if (res.data.success) {
      moment.comments = moment.comments || []
      moment.comments.push(res.data.data)
      moment.newComment = ''
      moment.showCommentInput = false
    }
  } catch (e) {
    console.error('Comment failed:', e)
  }
}

// ==================== 对话历史 ====================

interface SessionAgent {
  id: string
  name: string
  sessionCount: number
}

interface SessionRecord {
  sessionId: string
  sessionKey: string
  channel: string
  status: string
  updatedAt: string
  model?: string
  isReset?: boolean
}

interface SessionMessage {
  id: string
  role: string
  text: string
  timestamp: string
}

const selectedSessionAgent = ref<SessionAgent | null>(null)
const sessionsList = ref<SessionRecord[]>([])
const sessionsLoading = ref(false)
const selectedSession = ref<SessionRecord | null>(null)
const sessionMessages = ref<SessionMessage[]>([])

async function selectSessionAgent(agent: SessionAgent) {
  selectedSessionAgent.value = agent
  selectedSession.value = null
  sessionMessages.value = []
  sessionsLoading.value = true
  try {
    const res = await sessionApi.list(agent.id)
    if (res.data.success) {
      sessionsList.value = res.data.data
    }
  } catch (e) {
    console.error('Load sessions failed:', e)
  } finally {
    sessionsLoading.value = false
  }
}

async function selectSessionRecord(session: SessionRecord) {
  selectedSession.value = session
  sessionMessages.value = []
  if (!selectedSessionAgent.value) return
  try {
    const res = await sessionApi.messages(
      selectedSessionAgent.value.id,
      session.sessionId,
      session.isReset ? { isReset: true } : undefined
    )
    if (res.data.success) {
      sessionMessages.value = res.data.data
    }
  } catch (e) {
    console.error('Load messages failed:', e)
  }
}

// 弹窗打开时自动加载当前 Agent 数据
watch(showSessionsHistory, async (show) => {
  if (show && currentAgent.value) {
    // 自动选中当前 Agent
    const agent: SessionAgent = {
      id: currentAgent.value.id,
      name: currentAgent.value.name || currentAgent.value.id,
      sessionCount: 0
    }
    selectedSessionAgent.value = agent
    sessionAgents.value = [agent]
    await selectSessionAgent(agent)
  }
})

// ==================== 记忆功能 ====================

interface MemoryFile {
  date: string
  filename: string
  size: number
}

const selectedMemoryAgent = ref<SessionAgent | null>(null)
const memoryFiles = ref<MemoryFile[]>([])
const memoryLoading = ref(false)
const selectedMemoryFile = ref<MemoryFile | null>(null)
const memoryContent = ref('')

async function selectMemoryAgent(agent: SessionAgent) {
  selectedMemoryAgent.value = agent
  selectedMemoryFile.value = null
  memoryContent.value = ''
  memoryLoading.value = true
  try {
    const res = await memoryApi.list(agent.id)
    if (res.data.success) {
      memoryFiles.value = res.data.data
      // 更新 memoryCount
      agent.memoryCount = res.data.data.length
    }
  } catch (e) {
    console.error('Load memory files failed:', e)
  } finally {
    memoryLoading.value = false
  }
}

async function selectMemoryFile(file: MemoryFile) {
  selectedMemoryFile.value = file
  memoryContent.value = ''
  if (!selectedMemoryAgent.value) return
  try {
    const res = await memoryApi.get(selectedMemoryAgent.value.id, file.date)
    if (res.data.success) {
      memoryContent.value = res.data.data.content
    }
  } catch (e) {
    console.error('Load memory content failed:', e)
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 弹窗打开时自动加载当前 Agent 数据
watch(showMemory, async (show) => {
  if (show && currentAgent.value) {
    // 自动选中当前 Agent
    const agent: SessionAgent = {
      id: currentAgent.value.id,
      name: currentAgent.value.name || currentAgent.value.id,
      sessionCount: 0
    }
    selectedMemoryAgent.value = agent
    sessionAgents.value = [agent]
    await selectMemoryAgent(agent)
  }
})

function selectConversation(type: 'single' | 'group', id: string) {
  currentType.value = type
  selectedId.value = id

  const key = type === 'single' ? `single-${id}` : `group-${id}`

  // 获取 hostAgentId（群聊需要）
  const hostAgentId = type === 'single' ? id : groups.value.find(g => g.id === id)?.hostAgentId

  // 如果本地没有消息，从 Gateway 加载历史
  if (!messagesMap.value.has(key)) {
    loadChatHistory(key, hostAgentId, type === 'group')
  } else {
    messages.value = messagesMap.value.get(key) || []
  }

  scrollToBottom(false)
  // 如果 sessionKey 不存在才需要创建
  if (!sessionMap.value.has(key) && hostAgentId) {
    ensureSession(key, hostAgentId, type === 'group')
  }

  // 保存当前选中的会话
  saveToStorage()
}

async function loadChatHistory(key: string, agentId: string | undefined, isGroup: boolean) {
  if (!client) return

  // 获取已保存的 sessionKey
  let sessionKey = sessionMap.value.get(key)

  if (!sessionKey && agentId) {
    // 没有 sessionKey，需要创建新的
    await ensureSession(key, agentId, isGroup)
    sessionKey = sessionMap.value.get(key)
  }

  if (!sessionKey) return

  // 确保已订阅
  try {
    await client.request('sessions.subscribe', { keys: [sessionKey] })
  } catch (e) {
    console.error('Subscribe failed:', e)
  }

  try {
    const res = await client.request<{ messages?: any[] }>('chat.history', {
      sessionKey,
      limit: 100
    })
    const msgs = res.messages || []
    messagesMap.value.set(key, msgs)
    messages.value = msgs
    scrollToBottom(false)
  } catch (e) {
    console.error('Load history failed:', e)
  }
}

async function ensureSession(key: string, agentId: string, isGroup = false) {
  if (!client) return
  let sessionKey = sessionMap.value.get(key)
  if (sessionKey) return

  const sessionId = crypto.randomUUID()
  sessionKey = isGroup
    ? `agent:${agentId}:groupchat:${sessionId}`
    : `agent:${agentId}:webchat:${sessionId}`

  sessionMap.value.set(key, sessionKey)

  try {
    await client.request('sessions.subscribe', { keys: [sessionKey] })
  } catch (e) {
    console.error('Subscribe failed:', e)
  }
}

function getSenderName(msg: Message): string {
  if (msg.sourceName) return msg.sourceName
  if (msg.role === 'user') return userStore.user?.displayName || '你'
  return currentAgent.value?.name || 'Assistant'
}

function getMessageText(msg: Message): string {
  const content = msg.content
  if (Array.isArray(content)) {
    const textBlock = content.find(c => c.type === 'text')
    return textBlock?.text || ''
  }
  return ''
}

function renderMarkdown(text: string): string {
  return renderMessageContent(text)
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatShortTime(timestamp?: number): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  const ta = textareaRef.value
  if (ta) {
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 150) + 'px'
  }
}

async function sendMessage() {
  if (!canSend.value || !client) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''
  autoResize()

  const key = currentType.value === 'single' ? `single-${selectedId.value}` : `group-${selectedId.value}`

  const userMsg: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    content: [{ type: 'text', text: content }],
    timestamp: Date.now()
  }
  const msgs = messagesMap.value.get(key) || []
  msgs.push(userMsg)
  messagesMap.value.set(key, [...msgs])
  messages.value = [...msgs]

  // Update conversation preview
  if (currentType.value === 'single') {
    const conv = agentConvs.value.find(c => c.id === selectedId.value)
    if (conv) {
      conv.lastMessage = content.slice(0, 30)
      conv.lastTime = Date.now()
    }
  } else if (currentGroup.value) {
    currentGroup.value.lastMessage = content.slice(0, 30)
    currentGroup.value.lastTime = Date.now()
  }

  // 保存状态
  saveToStorage()

  let sessionKey = sessionMap.value.get(key)
  if (!sessionKey) {
    await ensureSession(key, currentType.value === 'single' ? selectedId.value : currentGroup.value!.hostAgentId, currentType.value === 'group')
    sessionKey = sessionMap.value.get(key)
  }
  if (!sessionKey) return

  let messageToSend = content
  if (currentType.value === 'group' && currentGroup.value) {
    const group = currentGroup.value
    const participantInfo = group.participants.filter(p => p.enabled).map(p => `- ${p.name}(${p.agentId})`).join('\n')
    messageToSend = `【群聊上下文】
主持人：${group.hostAgentName}
参与者：
${participantInfo}

【用户问题】
${content}

请根据问题决定需要哪些 Agent 参与，并使用 sessions_send 工具与他们讨论。`
  }

  // 设置当前会话的 streaming 状态
  streamingMap.value.set(key, true)
  streamContentMap.value.set(key, '')

  try {
    await client.request('chat.send', {
      sessionKey,
      message: messageToSend,
      deliver: false,
      idempotencyKey: crypto.randomUUID()
    })
  } catch (e: any) {
    console.error('Send failed:', e)
    streamingMap.value.set(key, false)
    streamContentMap.value.delete(key)
    ElMessage.error('发送失败: ' + e.message)
  }
}

function scrollToBottom(smooth = true) {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTo({
        top: messagesRef.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      })
    }
  })
}

function toggleParticipant(agentId: string) {
  const idx = newGroupParticipants.value.indexOf(agentId)
  if (idx >= 0) newGroupParticipants.value.splice(idx, 1)
  else newGroupParticipants.value.push(agentId)
}

function createGroup() {
  const host = agents.value.find(a => a.id === newGroupHost.value)
  const participants: Participant[] = newGroupParticipants.value.map(id => {
    const agent = agents.value.find(a => a.id === id)
    return { agentId: id, name: agent?.name || id, enabled: true }
  })

  const group: GroupChat = {
    id: `group-${crypto.randomUUID()}`,
    name: newGroupName.value || `${host?.name || '群'}的群`,
    hostAgentId: newGroupHost.value,
    hostAgentName: host?.name || newGroupHost.value,
    participants
  }

  groups.value.unshift(group)
  showCreateGroup.value = false
  newGroupName.value = ''
  newGroupHost.value = ''
  newGroupParticipants.value = []

  selectConversation('group', group.id)
  saveToStorage()
}

function saveToStorage() {
  // 只保存元信息，不保存完整聊天历史
  const data = {
    groups: groups.value,
    agentConvs: agentConvs.value,
    currentType: currentType.value,
    selectedId: selectedId.value,
    sessionMap: Object.fromEntries(sessionMap.value)
  }
  localStorage.setItem('feishu-chat-data', JSON.stringify(data))
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem('feishu-chat-data')
    if (raw) {
      const data = JSON.parse(raw)
      groups.value = data.groups || []
      // 恢复 sessionMap
      if (data.sessionMap) {
        sessionMap.value = new Map(Object.entries(data.sessionMap))
      }
      return data
    }
  } catch (e) {
    console.error('Load failed:', e)
  }
  return null
}

// ==================== 文件功能 ====================

async function loadAgentFiles() {
  const key = currentType.value === 'single' ? `single-${selectedId.value}` : `group-${selectedId.value}`
  const sessionKey = sessionMap.value.get(key)
  if (!sessionKey || !client) {
    console.log('[Files] No session or client')
    return
  }

  filesLoading.value = true
  filesError.value = null

  try {
    const result = await client.request<{ ok: boolean; artifacts: ArtifactFile[] }>('artifacts.list', {
      sessionId: sessionKey
    })
    agentFiles.value = result?.artifacts || []
  } catch (err: any) {
    console.error('[Files] Failed to load artifacts:', err)
    filesError.value = err.message || '加载失败'
  } finally {
    filesLoading.value = false
  }
}

async function handleFileClick(file: ArtifactFile) {
  try {
    const res = await chatApi.downloadArtifact({ path: file.path })
    if (res.data.success && res.data.data?.content) {
      const blob = new Blob([res.data.data.content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = file.name
      a.click()
      URL.revokeObjectURL(url)
    }
  } catch (err: any) {
    console.error('Failed to download artifact:', err)
    ElMessage.info(`文件路径: ${file.path}`)
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatFileDate(ms: number): string {
  const date = new Date(ms)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function onChatEvent(evt: any) {
  if (evt.event !== 'chat') return
  const payload = evt.payload
  const sessionKey = payload.sessionKey

  let convKey: string | null = null
  for (const [key, sk] of sessionMap.value.entries()) {
    if (sk === sessionKey) { convKey = key; break }
  }
  if (!convKey) return

  if (payload.state === 'delta') {
    const text = extractText(payload.message)
    if (typeof text === 'string') {
      streamContentMap.value.set(convKey, text)
      // 只有当前会话才滚动
      if (convKey === currentStreamKey.value) {
        scrollToBottom()
      }
    }
  } else if (payload.state === 'final') {
    const text = extractText(payload.message) || streamContentMap.value.get(convKey) || ''
    if (text?.trim()) {
      const msg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: [{ type: 'text', text }],
        timestamp: Date.now()
      }
      const msgs = messagesMap.value.get(convKey) || []
      msgs.push(msg)
      messagesMap.value.set(convKey, [...msgs])

      const currentKey = currentStreamKey.value
      if (convKey === currentKey) {
        messages.value = [...msgs]
      }

      // Update preview
      if (convKey.startsWith('single-')) {
        const agentId = convKey.replace('single-', '')
        const conv = agentConvs.value.find(c => c.id === agentId)
        if (conv) {
          conv.lastMessage = text.slice(0, 30)
          conv.lastTime = Date.now()
        }
      } else {
        const groupId = convKey.replace('group-', '')
        const group = groups.value.find(g => g.id === groupId)
        if (group) {
          group.lastMessage = text.slice(0, 30)
          group.lastTime = Date.now()
        }
      }
    }
    streamContentMap.value.delete(convKey)
    streamingMap.value.set(convKey, false)
    if (convKey === currentStreamKey.value) {
      scrollToBottom()
    }
    saveToStorage()
  } else if (payload.state === 'error') {
    streamContentMap.value.delete(convKey)
    streamingMap.value.set(convKey, false)
    ElMessage.error(payload.errorMessage || '错误')
  }
}

// ==================== Lifecycle ====================

onMounted(async () => {
  // 先加载存储的数据
  const savedData = loadFromStorage()

  try {
    const res = await agentApi.list()
    if (res.data.success) {
      agents.value = res.data.data || []
      // 初始化 agentConvs，并恢复保存的 lastMessage 和 lastTime
      const savedAgentConvs = savedData?.agentConvs || []
      const savedMap = new Map(savedAgentConvs.map((c: any) => [c.id, c]))

      agentConvs.value = agents.value.map(a => {
        const saved = savedMap.get(a.id)
        return {
          id: a.id,
          name: a.name || a.id,
          lastMessage: saved?.lastMessage || '',
          lastTime: saved?.lastTime || 0,
          unread: saved?.unread || 0
        }
      })
    }
  } catch (e) {
    console.error('Load agents failed:', e)
  }

  // 检查是否已有 Gateway 连接
  const existingClient = getGatewayClient()
  if (existingClient && existingClient.connected) {
    console.log('[FeishuChat] Reusing existing Gateway connection')
    client = existingClient
    // 更新事件回调
    ;(client as any).opts.onEvent = onChatEvent
  } else {
    // 需要新连接
    try {
      const res = await (await import('../api')).chatApi.getConfig()
      if (res.data.success) {
        const { gatewayUrl, gatewayToken } = res.data.data

        // 使用 Promise 等待连接成功
        await new Promise<void>((resolve) => {
          client = createGatewayClient({
            url: gatewayUrl,
            token: gatewayToken,
            onHello: () => {
              console.log('[FeishuChat] Connected')
              resolve()
            },
            onEvent: onChatEvent,
            onClose: () => {
              console.log('[FeishuChat] Disconnected')
            }
          })
          client.start()
          // 超时保护
          setTimeout(() => resolve(), 3000)
        })
      }
    } catch (e) {
      console.error('Connect gateway failed:', e)
    }
  }

  // Gateway 连接后再恢复上次选中的会话（这样才能加载历史）
  if (savedData?.currentType && savedData?.selectedId) {
    const type = savedData.currentType as 'single' | 'group'
    const id = savedData.selectedId

    // 检查会话是否还存在
    if (type === 'single' && agents.value.find(a => a.id === id)) {
      selectConversation('single', id)
    } else if (type === 'group' && groups.value.find(g => g.id === id)) {
      selectConversation('group', id)
    }
  }
})

onUnmounted(() => {
  saveToStorage()
  // 不停止 Gateway 连接，让其他组件复用
})

watch(messages, () => scrollToBottom())
watch(showFilesPanel, (show) => {
  if (show && currentConversation) {
    loadAgentFiles()
  }
})
</script>

<style scoped>
/* ==================== 设计系统 ==================== */
.feishu-chat {
  --bg-page: #f7f8fa;
  --bg-card: #ffffff;
  --bg-hover: #f0f2f5;
  --bg-active: #e8f4ff;
  --border-subtle: rgba(0, 0, 0, 0.06);
  --border-light: rgba(0, 0, 0, 0.08);
  --text-primary: #1a1a1a;
  --text-secondary: #5c5c5c;
  --text-tertiary: #8c8c8c;
  --text-placeholder: #b3b3b3;
  --accent: #3370ff;
  --accent-soft: rgba(51, 112, 255, 0.08);
  --accent-medium: rgba(51, 112, 255, 0.15);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.08);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;

  display: flex;
  height: 100%;
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ==================== 会话面板 ==================== */
.conversation-panel {
  width: 260px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  height: 58px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-btn:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 16px 16px;
  padding: 10px 14px;
  background: var(--bg-page);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all 0.2s;
}

.search-box:focus-within {
  background: var(--bg-card);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.search-box svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  border: none;
  background: none;
  font-size: 14px;
  color: var(--text-primary);
  letter-spacing: -0.1px;
}

.search-box input::placeholder {
  color: var(--text-placeholder);
}

.search-box input:focus {
  outline: none;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}

.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 2px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin: 1px 0;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.conversation-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
  transition: height 0.2s ease;
}

.conversation-item:hover {
  background: var(--bg-hover);
}

.conversation-item.active {
  background: var(--bg-active);
}

.conversation-item.active::before {
  height: 20px;
}

.conv-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease;
}

.conversation-item:hover .conv-avatar {
  transform: scale(1.02);
}

.conv-avatar.group {
  background: linear-gradient(135deg, var(--accent) 0%, #5b8def 100%);
  color: #fff;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-name {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.name-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.group-tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.2px;
}

.conv-preview {
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: -0.1px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.conv-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.conv-time {
  font-size: 11px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.conv-unread {
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  box-shadow: 0 1px 3px rgba(51, 112, 255, 0.4);
}

/* ==================== 聊天主区域 ==================== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-page);
  border-radius: 12px;
}

.chat-header {
  height: 58px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.header-avatar.group {
  background: linear-gradient(135deg, var(--accent) 0%, #5b8def 100%);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.header-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.header-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0.1px;
}

.header-btn {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  transition: all 0.2s;
}

.header-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* ==================== 消息区域 ==================== */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.02);
}

.messages-area::-webkit-scrollbar {
  width: 5px;
}

.messages-area::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.welcome {
  text-align: center;
  padding: 80px 20px;
}

.welcome-avatar {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  color: #fff;
  font-size: 32px;
  font-weight: 600;
  box-shadow: var(--shadow-lg);
}

.welcome-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: -0.3px;
}

.welcome-desc {
  font-size: 14px;
  color: var(--text-tertiary);
}

.message-row {
  display: flex;
  gap: 12px;
  animation: msgSlide 0.25s ease;
}

@keyframes msgSlide {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.msg-bubble {
  max-width: 68%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message-row.assistant .msg-bubble {
  background: var(--bg-card);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.message-row.user .msg-bubble {
  background: linear-gradient(135deg, var(--accent) 0%, #5b8def 100%);
  box-shadow: 0 2px 8px rgba(51, 112, 255, 0.25);
  margin-left: auto;
}

.msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.msg-sender {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.1px;
}

.msg-time {
  font-size: 11px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
  margin-top: 4px;
}

.message-row.user .msg-time {
  color: rgba(255, 255, 255, 0.7);
  text-align: right;
}

.typing-dots {
  display: inline-flex;
  gap: 3px;
  align-items: center;
}

.typing-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}

.typing-dots i:nth-child(2) { animation-delay: 0.15s; }
.typing-dots i:nth-child(3) { animation-delay: 0.3s; }

@keyframes pulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* Reading Indicator - Agent 正在思考 */
.reading-indicator {
  padding: 4px 0;
}

.reading-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 12px;
}

.reading-dots i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
  opacity: 0.6;
  transform: translateY(0);
  animation: readingBounce 1.2s ease-in-out infinite;
  will-change: transform, opacity;
}

.reading-dots i:nth-child(1) { animation-delay: 0s; }
.reading-dots i:nth-child(2) { animation-delay: 0.15s; }
.reading-dots i:nth-child(3) { animation-delay: 0.3s; }

@keyframes readingBounce {
  0%, 80%, 100% {
    opacity: 0.4;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-4px);
  }
}

/* 流式消息动画 */
.message-row.streaming .msg-text {
  animation: fadeIn 0.2s ease-out;
}

.msg-text {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  letter-spacing: -0.1px;
  color: var(--text-primary);
}

.message-row.user .msg-text {
  color: #fff;
}

/* ==================== 输入区域 ==================== */
.input-area {
  padding: 16px 0;
  background: var(--bg-card);
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-page);
  border-radius: 18px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.input-box:focus-within {
  background: var(--bg-card);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.input-tools {
  display: flex;
  gap: 4px;
}

.tool-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  transition: all 0.15s;
}

.tool-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.input-box textarea {
  flex: 1;
  border: none;
  background: none;
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-primary);
  resize: none;
  min-height: 40px;
  max-height: 200px;
  padding: 8px 0;
  font-family: inherit;
}

.input-box textarea::placeholder {
  color: var(--text-placeholder);
}

.input-box textarea:focus {
  outline: none;
}

.send-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: none;
  background: var(--bg-hover);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.send-btn.active {
  background: linear-gradient(135deg, var(--accent) 0%, #5b8def 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(51, 112, 255, 0.35);
}

.send-btn.active:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(51, 112, 255, 0.45);
}

/* ==================== 空状态 ==================== */
.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.empty-icon {
  opacity: 0.25;
  margin-bottom: 20px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
}

/* ==================== 详情面板 ==================== */
.detail-panel {
  width: 260px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
}

.detail-header {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.detail-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 14px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}

.member-avatar {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.member-name {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  letter-spacing: -0.1px;
}

.member-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.2px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.info-value.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--text-tertiary);
}

/* ==================== 弹窗 ==================== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.modal {
  width: 440px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  animation: modalSlide 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalSlide {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  padding: 22px 26px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.modal-body {
  padding: 26px;
}

.form-item {
  margin-bottom: 22px;
}

.form-item label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  letter-spacing: -0.1px;
}

.form-item input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--text-primary);
  transition: all 0.2s;
  letter-spacing: -0.1px;
}

.form-item input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.agent-select {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px 10px 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}

.agent-option:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.agent-option.selected {
  border-color: var(--accent);
  background: var(--accent-medium);
}

.agent-option .agent-avatar {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.agent-option span {
  font-size: 13px;
  color: var(--text-primary);
  letter-spacing: -0.1px;
}

.agent-option .check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
}

.modal-footer {
  padding: 18px 26px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel {
  padding: 10px 22px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  letter-spacing: -0.1px;
}

.btn-cancel:hover {
  background: var(--bg-hover);
}

.btn-confirm {
  padding: 10px 22px;
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--accent) 0%, #5b8def 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: -0.1px;
}

.btn-confirm:hover {
  box-shadow: 0 4px 12px rgba(51, 112, 255, 0.35);
  transform: translateY(-1px);
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ==================== 动画 ==================== */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* ==================== 文件面板 ==================== */
.files-panel {
  width: 280px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
}

.files-panel .panel-header {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.files-loading,
.files-error,
.files-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-tertiary);
  gap: 12px;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--accent-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.files-error {
  color: #ef4444;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.file-item:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
}

.refresh-btn {
  width: 100%;
  padding: 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--accent-medium);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==================== 朋友圈弹窗 ==================== */
.moments-modal {
  width: 480px;
  max-height: 80vh;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.moments-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.moments-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.moments-loading,
.moments-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-tertiary);
  gap: 12px;
}

.moments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.moment-item {
  background: var(--bg-page);
  border-radius: var(--radius-md);
  padding: 14px;
}

.moment-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.moment-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.moment-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.moment-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.moment-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.moment-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.moment-content {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  margin-bottom: 10px;
  white-space: pre-wrap;
}

.moment-img {
  margin-bottom: 10px;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.moment-img img {
  width: 100%;
  max-height: 240px;
  object-fit: cover;
}

.moment-actions {
  display: flex;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
}

.moment-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.moment-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.moment-action-btn.liked {
  color: #f56c6c;
}

.moment-comments {
  margin-top: 10px;
  padding: 10px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
}

.comment-line {
  font-size: 12px;
  margin-bottom: 4px;
}

.comment-line:last-child {
  margin-bottom: 0;
}

.comment-author {
  color: var(--accent);
  font-weight: 500;
}

.comment-input-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.comment-input-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  font-size: 13px;
  outline: none;
}

.comment-input-row input:focus {
  border-color: var(--accent);
}

.comment-input-row button {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

/* ==================== 对话历史弹窗 ==================== */
.history-modal {
  width: 720px;
  max-width: 90vw;
  height: 65vh;
  max-height: 80vh;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.history-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-modal-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.history-main {
  width: 280px;
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.history-loading,
.history-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  gap: 12px;
  padding: 20px;
}

.history-empty svg {
  opacity: 0.3;
}

.history-empty p {
  font-size: 13px;
}

.sessions-grid {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-card {
  padding: 12px 14px;
  background: var(--bg-page);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.session-card:hover {
  background: var(--bg-hover);
}

.session-card.active {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.session-card.reset {
  opacity: 0.7;
}

.session-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.session-channel {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--bg-hover);
  border-radius: 4px;
  color: var(--text-secondary);
}

.session-status {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.session-status.running {
  background: #fff7e6;
  color: #d46b08;
}

.session-status.idle,
.session-status.success {
  background: #f6ffed;
  color: #52c41a;
}

.session-status.reset {
  background: var(--bg-hover);
  color: var(--text-tertiary);
}

.session-card-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.session-card-model {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.history-detail {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
}

.history-detail-empty {
  background: var(--bg-page);
}

.detail-title {
  padding: 14px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-time {
  font-size: 11px;
  font-weight: 400;
  text-transform: none;
  color: var(--text-tertiary);
}

.detail-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-msg {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--bg-page);
}

.detail-msg .msg-content {
  overflow-x: auto;
}

.detail-msg .msg-content table {
  min-width: 400px;
}

.detail-msg.user {
  background: var(--accent-soft);
}

.msg-role {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}

.msg-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* ==================== 记忆弹窗 ==================== */
.memory-modal {
  width: 720px;
  max-width: 90vw;
  height: 65vh;
  max-height: 80vh;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.memory-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.memory-modal-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.memory-main {
  width: 240px;
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.memory-loading,
.memory-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  gap: 12px;
  padding: 20px;
}

.memory-empty svg {
  opacity: 0.3;
}

.memory-empty p {
  font-size: 13px;
}

.memory-files {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg-page);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.memory-file:hover {
  background: var(--bg-hover);
}

.memory-file.active {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.file-icon {
  font-size: 20px;
}

.file-info {
  flex: 1;
}

.file-date {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.file-size {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.memory-content-panel {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
}

.memory-content-empty {
  background: var(--bg-page);
}

.content-title {
  padding: 14px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-subtle);
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
}

.content-body :deep(h1) {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.content-body :deep(h2) {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  margin: 16px 0 8px;
}

.content-body :deep(h3) {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 6px;
}

.content-body :deep(p) {
  margin-bottom: 10px;
}

.content-body :deep(ul),
.content-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 10px;
}

.content-body :deep(li) {
  margin-bottom: 4px;
}

.content-body :deep(pre) {
  background: var(--bg-page);
  padding: 10px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-size: 12px;
}

.content-body :deep(code) {
  background: var(--bg-page);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.content-body :deep(blockquote) {
  border-left: 3px solid var(--accent);
  padding-left: 12px;
  margin: 10px 0;
  color: var(--text-secondary);
}

.content-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 13px;
}
</style>

<!-- 非 scoped 样式：用于 v-html 渲染的 markdown 内容 -->
<style>
.markdown-body {
  overflow-x: auto;
}

.markdown-body p {
  margin: 0;
}

.markdown-body p:last-child {
  margin-bottom: 0;
}

.markdown-body ul,
.markdown-body ol {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown-body li {
  margin: 4px 0;
}

.markdown-body code {
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 4px;
  font-size: 0.9em;
}

.markdown-body pre {
  margin: 8px 0;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-body pre code {
  background: none;
  padding: 0;
}

.markdown-body blockquote {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid var(--accent);
  background: rgba(99, 102, 241, 0.05);
  color: var(--text-secondary);
}

.markdown-body a {
  color: var(--accent);
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}

/* 表格样式 */
.markdown-body table {
  width: 100%;
  margin: 8px 0;
  border-collapse: collapse;
  font-size: 13px;
}

.markdown-body th,
.markdown-body td {
  padding: 8px 12px;
  border: 1px solid var(--border-light, #e8e5e1);
  text-align: left;
}

.markdown-body th {
  background: var(--bg-hover, #f5f3f0);
  font-weight: 600;
}

.markdown-body tr:nth-child(even) {
  background: rgba(0, 0, 0, 0.02);
}

.markdown-body tr:hover {
  background: rgba(0, 0, 0, 0.04);
}

/* 标题样式 */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin: 12px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}

.markdown-body h1 { font-size: 1.4em; }
.markdown-body h2 { font-size: 1.25em; }
.markdown-body h3 { font-size: 1.1em; }

/* 分隔线 */
.markdown-body hr {
  border: none;
  border-top: 1px solid var(--border-light, #e8e5e1);
  margin: 12px 0;
}
</style>