"""
日志配置模块

使用 Python 标准库 logging 实现，支持：
- 控制台输出（开发环境）
- 文件输出（按日期轮转）
- 异常追踪
- 结构化日志格式
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from flask import request, g
import json
import traceback


# 日志目录
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # 添加额外字段
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'resource'):
            log_data['resource'] = record.resource

        # 异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 保存原始 levelname
        orig_levelname = record.levelname
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        result = super().format(record)
        # 恢复原始 levelname
        record.levelname = orig_levelname
        return result


def setup_logging(app=None, level=logging.INFO):
    """
    配置日志系统

    Args:
        app: Flask 应用实例
        level: 日志级别
    """
    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器 - 所有日志
    all_logs_file = LOG_DIR / 'app.log'
    file_handler = logging.handlers.TimedRotatingFileHandler(
        all_logs_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # 文件处理器 - 错误日志
    error_logs_file = LOG_DIR / 'error.log'
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_logs_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # 第三方库日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # 创建应用日志器
    logger = get_logger('app')

    if app:
        # Flask 请求日志中间件
        @app.before_request
        def before_request():
            g.request_start_time = datetime.utcnow()
            g.request_id = request.headers.get('X-Request-ID', '-')

        @app.after_request
        def after_request(response):
            if request.path.startswith('/static') or request.path == '/favicon.ico':
                return response

            duration = None
            if hasattr(g, 'request_start_time'):
                duration = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000

            logger.info(
                f"{request.method} {request.path} - {response.status_code} - {duration:.2f}ms",
                extra={
                    'request_id': getattr(g, 'request_id', '-'),
                    'ip_address': request.remote_addr,
                }
            )
            return response

        @app.errorhandler(Exception)
        def handle_exception(e):
            logger.exception(
                f"Unhandled exception: {str(e)}",
                extra={
                    'request_id': getattr(g, 'request_id', '-'),
                    'ip_address': request.remote_addr,
                }
            )
            return {'success': False, 'error': '服务器内部错误'}, 500

    logger.info("日志系统初始化完成")
    return logger


def get_logger(name: str = 'app') -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称

    Returns:
        Logger 实例
    """
    return logging.getLogger(name)


class LogContext:
    """日志上下文管理器"""

    def __init__(self, logger, action, **kwargs):
        self.logger = logger
        self.action = action
        self.extra = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(f"开始: {self.action}", extra=self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        if exc_type:
            self.logger.error(
                f"失败: {self.action} - {exc_val} - {duration:.2f}ms",
                extra={**self.extra, 'exception': str(exc_val)},
                exc_info=True
            )
        else:
            self.logger.info(
                f"完成: {self.action} - {duration:.2f}ms",
                extra=self.extra
            )
        return False  # 不抑制异常


# 便捷函数
def log_operation(action: str, resource: str = None, user_id: int = None, **kwargs):
    """
    记录操作日志

    Args:
        action: 操作名称
        resource: 资源类型
        user_id: 用户 ID
        **kwargs: 额外信息
    """
    logger = get_logger('operation')
    extra = {
        'action': action,
        'resource': resource,
        'user_id': user_id,
        **kwargs
    }
    logger.info(action, extra=extra)


def log_error(message: str, exception: Exception = None, **kwargs):
    """
    记录错误日志

    Args:
        message: 错误消息
        exception: 异常对象
        **kwargs: 额外信息
    """
    logger = get_logger('error')
    logger.error(message, extra=kwargs, exc_info=exception is not None)


def log_api_call(method: str, endpoint: str, params: dict = None, response: dict = None, duration_ms: float = None):
    """
    记录 API 调用日志

    Args:
        method: HTTP 方法
        endpoint: 端点路径
        params: 请求参数
        response: 响应数据
        duration_ms: 耗时（毫秒）
    """
    logger = get_logger('api')
    logger.info(
        f"API调用: {method} {endpoint}",
        extra={
            'method': method,
            'endpoint': endpoint,
            'params': params,
            'response_status': response.get('success') if response else None,
            'duration_ms': duration_ms
        }
    )