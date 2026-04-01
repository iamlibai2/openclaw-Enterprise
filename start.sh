#!/bin/bash
# OpenClaw Admin UI 启动脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "  OpenClaw Admin UI"
echo "=========================================="

# 启动后端
echo "启动后端服务..."
cd backend
pip3 install -q flask flask-cors 2>/dev/null
python3 app.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 2

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 启动前端
echo "启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  服务已启动:"
echo "  - 后端 API: http://127.0.0.1:5001"
echo "  - 前端 UI:  http://localhost:5000"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户停止
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait