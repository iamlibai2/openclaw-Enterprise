import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import { initDatabase, cleanupExpiredSessions } from './database';
import authRoutes from './routes/auth';
import usersRoutes from './routes/users';
import logsRoutes from './routes/logs';
import gatewayRoutes from './routes/gateway';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5001;

// 安全中间件
app.use(helmet());

// CORS 配置
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:5002',
  credentials: true
}));

// 请求限制
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 100, // 每个IP最多100请求
  message: { success: false, message: '请求过于频繁，请稍后再试' }
});
app.use('/api/auth/login', limiter);
app.use('/api/auth/register', limiter);

// JSON 解析
app.use(express.json());

// 请求日志中间件
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path} - IP: ${req.ip}`);
  next();
});

// API 路由
app.use('/api/auth', authRoutes);
app.use('/api/users', usersRoutes);
app.use('/api/logs', logsRoutes);
app.use('/api/gateway', gatewayRoutes);

// 健康检查（无需认证）
app.get('/api/health', (req, res) => {
  res.json({ success: true, status: 'ok', timestamp: new Date().toISOString() });
});

// 404 处理
app.use((req, res) => {
  res.status(404).json({ success: false, message: '接口不存在' });
});

// 错误处理
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('错误:', err);
  res.status(500).json({ success: false, message: '服务器内部错误' });
});

// 启动服务器
async function startServer() {
  try {
    // 初始化数据库
    await initDatabase();
    console.log('✅ 数据库初始化完成');

    // 清理过期会话（定时任务）
    setInterval(cleanupExpiredSessions, 60 * 60 * 1000); // 每小时清理一次

    app.listen(PORT, () => {
      console.log(`🚀 后端服务器已启动: http://localhost:${PORT}`);
      console.log(`📝 默认管理员账户: admin / admin123`);
    });
  } catch (error) {
    console.error('启动失败:', error);
    process.exit(1);
  }
}

startServer();