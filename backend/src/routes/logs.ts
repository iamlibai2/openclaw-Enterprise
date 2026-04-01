import { Router, Request, Response } from 'express';
import { authMiddleware, requirePermission } from '../auth';
import { listLogs, countLogs, createLog } from '../database';

const router = Router();

router.use(authMiddleware);

// 获取操作日志列表
router.get('/', requirePermission('audit:read'), async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 100;
    const offset = parseInt(req.query.offset as string) || 0;

    const logs = await listLogs(limit, offset);
    const total = await countLogs();

    return res.json({
      success: true,
      logs,
      pagination: {
        total,
        limit,
        offset,
        hasMore: offset + limit < total
      }
    });
  } catch (error) {
    return res.status(500).json({ success: false, message: '获取日志失败' });
  }
});

// 获取用户自己的操作日志
router.get('/me', async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;

    const logs = await listLogsByUser(req.user!.userId, limit);

    return res.json({ success: true, logs });
  } catch (error) {
    return res.status(500).json({ success: false, message: '获取日志失败' });
  }
});

// 辅助函数
async function listLogsByUser(userId: string, limit: number): Promise<any[]> {
  const db = require('../database').default;

  return new Promise((resolve, reject) => {
    db.all(
      'SELECT * FROM operation_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
      [userId, limit],
      (err: Error | null, rows: any[]) => {
        if (err) reject(err);
        else resolve(rows);
      }
    );
  });
}

export default router;