#!/bin/bash
# CLI功能测试脚本

echo "=== 网易云音乐CLI功能测试 ==="
echo ""

# 使用uv运行Python
PYTHON="uv run python"

# 测试计数器
TOTAL=0
PASSED=0
FAILED=0

# 测试函数
test_case() {
    local name="$1"
    local command="$2"
    local expected_exit="$3"

    TOTAL=$((TOTAL + 1))
    echo "测试 $TOTAL: $name"

    eval "$command" >/dev/null 2>&1
    actual_exit=$?

    if [ $actual_exit -eq $expected_exit ]; then
        echo "  ✓ 通过（退出码: $actual_exit）"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ 失败（期望退出码: $expected_exit, 实际: $actual_exit）"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# 执行测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. 基础命令测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_case "健康检查" "$PYTHON cli.py health" 0
test_case "获取歌曲URL" "$PYTHON cli.py song 185668" 0
test_case "获取歌曲详情" "$PYTHON cli.py song 185668 --type name" 0
test_case "获取歌词" "$PYTHON cli.py song 185668 --type lyric" 0
test_case "搜索歌曲" "$PYTHON cli.py search '周杰伦' --limit 5" 0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. 输出格式测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_case "JSON输出（默认）" "$PYTHON cli.py health" 0
test_case "人类可读输出" "$PYTHON cli.py --output human health" 0
test_case "静默模式" "$PYTHON cli.py --quiet health" 0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. URL输入支持测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_case "歌曲URL解析" "$PYTHON cli.py song 'https://music.163.com/song?id=185668'" 0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. 错误处理测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_case "缺少必需参数" "$PYTHON cli.py song" 2
test_case "未知命令" "$PYTHON cli.py unknown_command" 2

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. JSON输出格式验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "测试: JSON结构验证"
JSON_OUTPUT=$($PYTHON cli.py health 2>/dev/null)
if echo "$JSON_OUTPUT" | jq -e '.success' >/dev/null 2>&1; then
    echo "  ✓ JSON格式正确，包含success字段"
    PASSED=$((PASSED + 1))
else
    echo "  ✗ JSON格式错误"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))
echo ""

# 输出测试结果
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试结果汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "总计: $TOTAL"
echo "通过: $PASSED"
echo "失败: $FAILED"
echo "通过率: $(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 所有测试通过！"
    exit 0
else
    echo "⚠️  有 $FAILED 个测试失败"
    exit 1
fi
