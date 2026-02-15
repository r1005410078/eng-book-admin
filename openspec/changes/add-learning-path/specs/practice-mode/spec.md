## ADDED Requirements

### Requirement: 互动练习模式与人性化机制
系统 MUST 支持语言学习的互动练习模式，并提供人性化的跳过与豁免机制，避免用户学习受阻。

- **类型**: 至少支持 `Shadowing` (跟读/影子练习) 和 `Listening` (听力填空)。
- **Skipping Logic**: 系统 MUST 支持配置“允许跳过练习”或“最大失败次数豁免”。当用户连续 N 次失败后，系统提示并允许用户跳过该练习，继续下一课时。
- **提交**: 提供 API 接口供用户提交练习结果（例如：音频文件、填写后的文本）。
- **评估**: 实现评估提交内容的机制（例如：字符串匹配、通过外部服务进行音频分析）。

#### Scenario: 练习多次失败后跳过
- **WHEN** 用户在“听力填空”练习中连续 3 次未能达到及格分数
- **THEN** 系统弹出“跳过练习”选项
- **AND** 用户点击跳过
- **AND** 系统将该课时标记为 `COMPLETED (SKIPPED)`，并解锁下一课

### Requirement: 练习驱动的进度
完成练习 MUST 作为课时完成的条件之一，除非触发了上述的跳过机制。
- 一个课时可能需要通过练习会话（例如：达到最低分数）才能标记为 `COMPLETED`。

#### Scenario: 练习通过后完成课时
- **WHEN** 用户在该课时的练习模式中达到及格分数（例如：>80%）
- **THEN** 关联课时的状态更新为 `COMPLETED`

### Requirement: 互动练习接口 (Practice Submission)
为了支持前端 App 的练习模式，系统 MUST 提供提交练习结果和查询历史的 API。

- **提交练习结果 (Submit Practice)**: 提供 `POST /api/v1/lessons/{id}/practice` 接口。
  - **Type**: 支持多种练习类型（SHADOWING, LISTENING, FILL_BLANK）。
  - **Body**: `{ "type": "SHADOWING", "score": 85, "audio_url": "optional_upload", "details": {...} }`
  - **Logic**: 
    - 记录到 `practice_submissions` 表。
    - 如果分数 >= Passing Score，可能触发 Lesson Progress = COMPLETED (如果是练习驱动模式)。

- **查询练习历史 (Practice History)**: 提供 `GET /api/v1/lessons/{id}/practice` 接口。
  - **Response**: List of submissions ordered by time desc.
