#!/bin/bash

# 网易云音乐API一键启动脚本（使用uv）

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
echo -e "${GREEN}   (使用uv管理依赖)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo -e "${RED}错误: 未找到uv命令${NC}"
    echo "请安装uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} 找到uv: $(uv --version)"

# 检查pyproject.toml是否存在
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}错误: 未找到pyproject.toml文件${NC}"
    echo "请在项目根目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
echo ""
echo "检查虚拟环境..."
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠${NC} 虚拟环境不存在，正在创建..."
    uv sync
    echo -e "${GREEN}✓${NC} 虚拟环境创建完成"
else
    echo -e "${GREEN}✓${NC} 虚拟环境已存在"
fi

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

# 使用uv run启动服务
uv run python main.py
