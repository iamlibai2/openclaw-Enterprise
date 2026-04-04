# Agent 模板库

本目录包含预设的 Agent 模板，用于快速创建新的 Agent。

## 模板列表

| 模板名 | ID | 适用场景 | 工具权限 |
|--------|-----|----------|----------|
| 行政助理 | admin_assistant | 日程管理、文档整理、会议安排 | messaging |
| 代码助手 | code_assistant | 编程开发、代码审查、Bug修复 | full |
| 客服代表 | customer_service | 客户问答、工单处理、服务支持 | messaging |
| 写作助手 | writing_assistant | 内容创作、文案撰写、文章编辑 | messaging |

## 模板结构

每个模板目录包含以下文件：

```
模板名/
├── manifest.json    # 元数据（名称、描述、推荐配置）
├── soul.md          # 灵魂文件（核心特质、边界、风格）
├── identity.md      # 身份文件（名字、职责、能力）
├── user.md          # 主人信息模板（创建后需更新）
├── skills.json      # 技能配置（默认为空）
├── tools.json       # 工具权限配置
└── model.json       # 模型配置
```

## 使用方式

1. 通过 Admin UI 的 Agent 创建向导选择模板
2. 系统读取模板文件，通过 Gateway API 创建新 Agent
3. 用户在档案页面更新 USER.md 等个性化内容

## 创建新模板

1. 复制现有模板目录作为起点
2. 修改 manifest.json 的 name、id、description
3. 编辑 soul.md、identity.md 等文件
4. 调整 tools.json 的工具权限

## 注意事项

- 模板中的 skills.json 默认为空，因为技能需要先安装才能使用
- tools.json 的 profile 可选值：`messaging`, `full`, `default`
- 模板的 user.md 是模板内容，创建 Agent 后需要用户更新