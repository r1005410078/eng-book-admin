# 异步视频处理 - 快速开始指南

## 🚀 新功能概述

系统现已支持异步视频处理和实时进度查询！

### 主要改进

1. **异步触发** - 立即返回响应，无需等待
2. **进度查询** - 实时了解任务状态
3. **并发保护** - 防止重复处理
4. **详细进度** - 查看每个子任务的状态

## 📖 API 使用指南

### 1. 异步触发视频处理（调试用）

**端点**: `POST /api/v1/videos/{video_id}/run_sync`

**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/videos/1/run_sync" \
  -H "Content-Type: application/json"
```

**响应** (202 Accepted):
```json
{
  "message": "任务已启动",
  "video_id": 1,
  "task_id": null,
  "status": "pending"
}
```

**可选参数**:
- `force=true` - 强制重新处理（即使有正在进行的任务）

```bash
curl -X POST "http://localhost:8000/api/v1/videos/1/run_sync?force=true"
```

### 2. 触发视频重新处理

**端点**: `POST /api/v1/videos/{video_id}/reprocess`

**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/videos/1/reprocess" \
  -H "Content-Type: application/json"
```

**响应** (202 Accepted):
```json
{
  "message": "任务已启动",
  "video_id": 1,
  "task_id": "celery-task-uuid-here",
  "status": "pending"
}
```

### 3. 查询处理进度

**端点**: `GET /api/v1/videos/{video_id}/reprocess`

**请求**:
```bash
curl -X GET "http://localhost:8000/api/v1/videos/1/reprocess"
```

**响应** (200 OK):
```json
{
  "video_id": 1,
  "status": "processing",
  "progress": 45,
  "tasks": [
    {
      "name": "audio_extraction",
      "status": "completed",
      "progress": 100
    },
    {
      "name": "subtitle_generation",
      "status": "processing",
      "progress": 50
    },
    {
      "name": "translation",
      "status": "pending",
      "progress": 0
    },
    {
      "name": "phonetic",
      "status": "pending",
      "progress": 0
    },
    {
      "name": "grammar_analysis",
      "status": "pending",
      "progress": 0
    }
  ],
  "started_at": "2026-01-11T10:00:00Z",
  "updated_at": "2026-01-11T10:05:30Z"
}
```

## 🔄 完整工作流示例

### Python 示例

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"
video_id = 1

# 1. 触发视频处理
response = requests.post(f"{BASE_URL}/videos/{video_id}/run_sync")
assert response.status_code == 202
print(f"任务已启动: {response.json()}")

# 2. 轮询查询进度
while True:
    progress = requests.get(f"{BASE_URL}/videos/{video_id}/reprocess").json()
    
    print(f"总体进度: {progress['progress']}%")
    print(f"状态: {progress['status']}")
    
    # 显示子任务进度
    for task in progress['tasks']:
        print(f"  - {task['name']}: {task['status']} ({task['progress']}%)")
    
    # 检查是否完成
    if progress['status'] in ['completed', 'failed']:
        print(f"处理完成！最终状态: {progress['status']}")
        break
    
    # 等待 2 秒后再查询
    time.sleep(2)
```

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';
const videoId = 1;

// 1. 触发视频处理
async function startProcessing() {
  const response = await fetch(`${BASE_URL}/videos/${videoId}/run_sync`, {
    method: 'POST'
  });
  
  if (response.status === 202) {
    const data = await response.json();
    console.log('任务已启动:', data);
    return true;
  }
  return false;
}

// 2. 查询进度
async function checkProgress() {
  const response = await fetch(`${BASE_URL}/videos/${videoId}/reprocess`);
  const progress = await response.json();
  
  console.log(`总体进度: ${progress.progress}%`);
  console.log(`状态: ${progress.status}`);
  
  progress.tasks.forEach(task => {
    console.log(`  - ${task.name}: ${task.status} (${task.progress}%)`);
  });
  
  return progress;
}

// 3. 完整流程
async function processVideo() {
  // 启动处理
  await startProcessing();
  
  // 轮询进度
  const interval = setInterval(async () => {
    const progress = await checkProgress();
    
    if (progress.status === 'completed' || progress.status === 'failed') {
      console.log(`处理完成！最终状态: ${progress.status}`);
      clearInterval(interval);
    }
  }, 2000);
}

processVideo();
```

## 📊 进度计算说明

总体进度基于以下权重计算：

| 任务 | 权重 | 说明 |
|------|------|------|
| audio_extraction | 10% | 音频提取 |
| subtitle_generation | 20% | 字幕生成 |
| translation | 30% | 翻译 |
| phonetic | 20% | 音标标注 |
| grammar_analysis | 20% | 语法分析 |

**计算公式**:
```
总进度 = Σ(子任务进度 × 子任务权重)
```

**示例**:
- audio_extraction: 100% (完成)
- subtitle_generation: 50% (进行中)
- 其他: 0% (未开始)

总进度 = 100% × 10% + 50% × 20% + 0% × 70% = 10% + 10% = 20%

## ⚠️ 错误处理

### 并发冲突 (409 Conflict)

**场景**: 视频正在处理中，再次触发处理

**响应**:
```json
{
  "detail": "该视频正在处理中，请稍后再试或使用 force=true 强制重新处理"
}
```

**解决方案**:
1. 等待当前任务完成
2. 或使用 `force=true` 强制重新处理

### 视频不存在 (404 Not Found)

**场景**: 视频 ID 不存在

**响应**:
```json
{
  "detail": "视频不存在"
}
```

### 任务不存在 (404 Not Found)

**场景**: 查询进度时，视频从未被处理过

**响应**:
```json
{
  "detail": "未找到处理任务"
}
```

## 🎯 最佳实践

### 1. 轮询间隔

建议轮询间隔：**2-5 秒**

```python
# 推荐
time.sleep(2)

# 不推荐（太频繁）
time.sleep(0.5)
```

### 2. 超时处理

建议设置超时时间，避免无限等待：

```python
import time

MAX_WAIT_TIME = 600  # 10 分钟
start_time = time.time()

while True:
    if time.time() - start_time > MAX_WAIT_TIME:
        print("处理超时！")
        break
    
    progress = check_progress()
    if progress['status'] in ['completed', 'failed']:
        break
    
    time.sleep(2)
```

### 3. 错误重试

对于网络错误，建议实现重试机制：

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def get_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = get_session()
response = session.get(f"{BASE_URL}/videos/{video_id}/reprocess")
```

## 🔧 故障排查

### 问题 1: 进度一直是 0%

**可能原因**:
- Celery worker 未启动
- 任务队列阻塞

**解决方案**:
```bash
# 检查 Celery worker 状态
celery -A app.tasks inspect active

# 重启 Celery worker
celery -A app.tasks worker --loglevel=info
```

### 问题 2: 状态一直是 "processing"

**可能原因**:
- 任务执行失败但未更新状态
- 数据库连接问题

**解决方案**:
```bash
# 检查数据库中的任务状态
psql -d your_database -c "SELECT * FROM processing_tasks WHERE video_id = 1;"

# 检查应用日志
tail -f logs/app.log
```

### 问题 3: 返回 409 Conflict

**原因**: 视频正在处理中

**解决方案**:
```bash
# 等待当前任务完成，或使用 force 参数
curl -X POST "http://localhost:8000/api/v1/videos/1/run_sync?force=true"
```

## 📚 相关文档

- **API 文档**: http://localhost:8000/docs
- **设计文档**: `openspec/changes/async-video-processing/design.md`
- **实施总结**: `openspec/changes/async-video-processing/IMPLEMENTATION_SUMMARY.md`

## 🆘 获取帮助

如有问题，请查看：
1. API 文档（Swagger UI）
2. 应用日志
3. Celery worker 日志
4. 数据库任务记录

---

**更新时间**: 2026-01-11  
**版本**: 1.0.0
