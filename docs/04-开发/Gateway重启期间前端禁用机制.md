# Gateway 重启期间前端禁用机制

## 概述

当执行需要 Gateway 重启的操作时（如创建 Agent、创建/删除模型），前端界面需要在重启期间禁用用户操作，防止重复提交或数据不一致。

---

## 重启触发条件

| 操作 | 是否重启 | API |
|------|---------|-----|
| 创建 Agent | ✅ 重启 | `agents.create` |
| 编辑 Agent | ❌ 热加载 | `agents.update` |
| 删除 Agent | ❌ 热加载 | `agents.delete` |
| 创建模型 | ✅ 重启 | `config.apply` |
| 编辑模型 | ❌ 不重启 | 直接保存数据库 |
| 删除模型 | ✅ 重启 | `config.apply` |

---

## 实现方案

### 1. 状态定义

```typescript
const isRestarting = ref(false)  // Gateway 是否正在重启
```

### 2. 操作流程

```typescript
async function submitCreate() {
  // 1. 确认对话框
  await ElMessageBox.confirm('创建将重启 Gateway，是否继续？')

  // 2. 开始重启，禁用界面
  isRestarting.value = true

  // 3. 显示提示
  const loadingMsg = ElMessage({
    message: '正在创建并重启 Gateway，请稍候...',
    type: 'info',
    duration: 0
  })

  try {
    // 4. 调用后端 API
    await api.create(data)
    ElMessage.success('创建成功')
  } finally {
    // 5. 重启完成，恢复界面
    loadingMsg.close()
    isRestarting.value = false
  }
}
```

### 3. UI 禁用

**列表页面**：

```vue
<!-- 表格 loading -->
<el-card v-loading="loading || isRestarting"
         element-loading-text="Gateway 正在重启，请稍候...">
  <el-table :data="paginatedData">
    <!-- 操作按钮禁用 -->
    <el-button :disabled="isRestarting">编辑</el-button>
    <el-button :disabled="isRestarting">删除</el-button>
  </el-table>
</el-card>

<!-- 新建按钮禁用 -->
<el-button :disabled="isRestarting">新建</el-button>
```

**对话框**：

```vue
<el-form>
  <!-- 所有输入项禁用 -->
  <el-input :disabled="isRestarting" />
  <el-select :disabled="isRestarting" />
  <el-switch :disabled="isRestarting" />
</el-form>

<template #footer>
  <!-- 取消按钮禁用 -->
  <el-button :disabled="isRestarting">取消</el-button>
  <!-- 提交按钮已有 loading 状态 -->
  <el-button type="primary" :loading="submitting">创建</el-button>
</template>
```

---

## 样式

```css
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
```

---

## 注意事项

1. **不要关闭对话框**：重启期间保持对话框打开，防止用户重新打开重复操作
2. **禁用取消按钮**：防止用户关闭对话框后再次点击
3. **表格 loading**：让用户知道系统正在处理
4. **热加载操作**：编辑 Agent、删除 Agent 不需要禁用（热加载，秒级完成）

---

## 扩展：Gateway 状态监控

未来可以添加实时状态监控：

```typescript
// 心跳检测
async function checkGatewayStatus() {
  try {
    await sync_call('config.get')
    return 'online'
  } catch {
    return 'offline'
  }
}

// SSE 推送状态
eventSource.addEventListener('gateway:restarting', () => {
  isRestarting.value = true
})

eventSource.addEventListener('gateway:ready', () => {
  isRestarting.value = false
})
```