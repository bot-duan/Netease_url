#!/bin/bash

# 网易云音乐API一键启动脚本

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   网易云音乐API服务启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查conda是否安装
if ! command -v conda &> /dev/null; then
    echo -e "${RED}错误: 未找到conda命令${NC}"
    echo "请确保已安装Anaconda或Miniconda"
    exit 1
fi

# 检查环境是否存在
if conda env list | grep -q "^netease "; then
    echo -e "${GREEN}✓${NC} 找到conda环境: netease"
else
    echo -e "${YELLOW}⚠${NC} 未找到conda环境 'netease'"
    echo "正在创建环境..."
    conda create -n netease python=3.9 -y
    echo -e "${GREEN}✓${NC} 环境创建完成"
fi

# 检查依赖是否安装
echo ""
echo "检查项目依赖..."

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: 未找到requirements.txt文件${NC}"
    exit 1
fi

# 使用conda run检查依赖
echo "正在检查Python依赖..."
conda run -n netease python -c "import flask" 2>/dev/null || {
    echo -e "${YELLOW}⚠${NC} 依赖未完整安装，正在安装..."
    conda run -n netease pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} 依赖安装完成"
}

# 检查Cookie文件
echo ""
if [ -f "cookie.txt" ]; then
    if [ -s "cookie.txt" ]; then
        echo -e "${GREEN}✓${NC} Cookie文件存在"
    else
        echo -e "${YELLOW}⚠${NC} Cookie文件为空，可能需要配置"
    fi
else
    echo -e "${YELLOW}⚠${NC} 未找到cookie.txt文件"
    echo "请将网易云音乐黑胶会员Cookie保存到cookie.txt中"
fi

# 启动服务
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   正在启动服务...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 使用conda run --no-capture-output启动，实时显示所有输出
# 不使用exec，让脚本正常等待子进程结束
conda run --no-capture-output -n netease python main.py
