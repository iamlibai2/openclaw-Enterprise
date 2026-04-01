import { Router, Request, Response } from 'express';
import { authMiddleware, requirePermission } from '../auth';
import { createLog } from '../database';
import { exec } from 'child_process';

const router = Router();

router.use(authMiddleware);

// 获取 Gateway 状态
router.get('/status', async (req: Request, res: Response) => {
  try {
    // 检查 Gateway 进程状态
    const isRunning = await checkGatewayStatus();

    return res.json({
      success: true,
      status: isRunning ? 'running' : 'stopped',
      uptime: '计算中...',
      activeSessions: 0
    });
  } catch (error) {
    return res.status(500).json({ success: false, message: '获取状态失败' });
  }
});

// 启动 Gateway
router.post('/start', requirePermission('gateway:write'), async (req: Request, res: Response) => {
  try {
    await executeCommand('openclaw gateway start');

    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'gateway_start',
      resource: 'gateway',
      details: '启动 Gateway',
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: 'Gateway 启动成功' });
  } catch (error) {
    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'gateway_start',
      resource: 'gateway',
      details: '启动 Gateway 失败',
      ip_address: req.ip || 'unknown',
      status: 'failure'
    });

    return res.status(500).json({ success: false, message: '启动失败' });
  }
});

// 停止 Gateway
router.post('/stop', requirePermission('gateway:manage'), async (req: Request, res: Response) => {
  try {
    await executeCommand('openclaw gateway stop');

    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'gateway_stop',
      resource: 'gateway',
      details: '停止 Gateway',
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: 'Gateway 停止成功' });
  } catch (error) {
    return res.status(500).json({ success: false, message: '停止失败' });
  }
});

// 重启 Gateway
router.post('/restart', requirePermission('gateway:write'), async (req: Request, res: Response) => {
  try {
    await executeCommand('openclaw gateway restart');

    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'gateway_restart',
      resource: 'gateway',
      details: '重启 Gateway',
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: 'Gateway 重启成功' });
  } catch (error) {
    return res.status(500).json({ success: false, message: '重启失败' });
  }
});

// 刷新配置
router.post('/reload', requirePermission('config:write'), async (req: Request, res: Response) => {
  try {
    // 这里可以调用 Gateway 的配置刷新接口
    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'config_reload',
      resource: 'config',
      details: '刷新配置',
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: '配置已刷新' });
  } catch (error) {
    return res.status(500).json({ success: false, message: '刷新失败' });
  }
});

// 辅助函数
async function checkGatewayStatus(): Promise<boolean> {
  return new Promise((resolve) => {
    exec('pgrep -f "openclaw gateway"', (error, stdout) => {
      resolve(stdout.trim().length > 0);
    });
  });
}

async function executeCommand(command: string): Promise<void> {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
  });
}

export default router;