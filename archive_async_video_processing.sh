#!/bin/bash
# OpenSpec 手动归档脚本 - async-video-processing

set -e

echo "=========================================="
echo "OpenSpec 手动归档 - async-video-processing"
echo "=========================================="
echo ""

CHANGE_ID="async-video-processing"
DATE=$(date +%Y-%m-%d)
ARCHIVE_DIR="openspec/changes/archive/${DATE}-${CHANGE_ID}"

# 1. 创建归档目录
echo "1. 创建归档目录..."
mkdir -p openspec/changes/archive
echo "   ✓ 归档目录已创建"

# 2. 移动变更到归档
echo ""
echo "2. 移动变更到归档..."
if [ -d "openspec/changes/${CHANGE_ID}" ]; then
    mv "openspec/changes/${CHANGE_ID}" "${ARCHIVE_DIR}"
    echo "   ✓ 已移动到: ${ARCHIVE_DIR}"
else
    echo "   ✗ 错误: openspec/changes/${CHANGE_ID} 不存在"
    exit 1
fi

# 3. 检查是否需要更新规格文件
echo ""
echo "3. 检查规格文件..."
SPEC_FILE="openspec/specs/video-processing/spec.md"

if [ -f "${SPEC_FILE}" ]; then
    echo "   ⚠️  规格文件已存在: ${SPEC_FILE}"
    echo "   ⚠️  需要手动合并增量到规格文件"
    echo "   ⚠️  增量位置: ${ARCHIVE_DIR}/specs/video-processing/spec.md"
else
    echo "   ℹ️  规格文件不存在，可能 add-video-processing 还未归档"
    echo "   ℹ️  建议等待 add-video-processing 一起归档"
fi

# 4. 提交归档
echo ""
echo "4. 提交归档..."
git add openspec/changes/archive/
git commit -m "chore: 归档 async-video-processing 变更到 ${DATE}"
echo "   ✓ 归档已提交"

echo ""
echo "=========================================="
echo "归档完成！"
echo "=========================================="
echo ""
echo "归档位置: ${ARCHIVE_DIR}"
echo ""
echo "下一步:"
echo "1. 如果需要，手动合并规格增量"
echo "2. 验证所有测试仍然通过"
echo "3. 更新相关文档链接"
echo ""
