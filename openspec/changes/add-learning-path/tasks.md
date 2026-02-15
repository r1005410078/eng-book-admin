# 任务列表

## 1. 课程结构与极简接口
- [x] 1.1 创建 `courses`, `units`, `lessons` 及 `task_journals` 的数据库迁移脚本。
  - **Schema**: 明确 `lessons` 与 `videos` 之间的级联删除/软删除 (Soft Delete) 策略。
- [x] 1.2 实现 **上传课程 (Upload Course)** 流程 API。
- [x] 1.3 实现 **修改课程 (Modify Course)** 接口。
- [x] 1.4 实现 **获取进度 (Get Progress)** 接口。
- [ ] 1.5 实现后台 **Reconciler**: 
  - 自动任务恢复。
  - **GC (Garbage Collection)**: 定期清理已软删除的 Lesson 所关联的孤儿文件 (Orphaned Files)。
- [x] 1.6 实现 **动静分离的内容查询 (Get Lesson Content)** 接口。
- [x] 1.7 添加极简接口及任务流的测试。
- [ ] 1.8 实现 **字幕数据查询 (Get Lesson Subtitles)** 接口。
  - **Spec**: `specs/subtitle-api/spec.md`
  - 返回完整字幕数据（原文、翻译、音标、语法分析）
  - 使用 `joinedload` 优化查询性能
- [ ] 1.9 实现 **后台任务列表 (Get Task List)** 接口。
  - **Spec**: `specs/tasks-api/spec.md`
  - 支持分页、按状态和类型筛选
  - 用于监控后台处理进度

## 2. 学习进度及互动反馈
- [ ] 2.1 创建 `user_progress` 表的数据库迁移脚本。
- [ ] 2.2 实现课程、单元和课时层级的进度追踪逻辑。
- [ ] 2.3 实现更新课时完成状态的 API 接口。
- [ ] 2.4 实现获取当前用户进度的 API 接口。
- [ ] 2.5 实现顺序学习的“解锁”逻辑。
  - **Logic**: 支持 `SKIPPED` 状态也视为“已完成”以解锁下一课。
- [ ] 2.6 实现语法提问接口。
- [ ] 2.7 添加进度追踪及互动功能的测试。

## 3. 练习模式
- [ ] 3.1 创建 `practice_submissions` 表的数据库迁移脚本。
- [ ] 3.2 定义练习类型（跟读、听力、填空）。
- [ ] 3.3 实现提交练习结果的 API 接口。
- [ ] 3.4 实现获取练习历史/分数的 API 接口。
- [ ] 3.5 将练习完成情况与课时进度集成。
  - **Logic**: 实现“连续失败 N 次允许跳过”或“强制跳过”的后台配置逻辑。
- [ ] 3.6 添加练习提交的测试。
