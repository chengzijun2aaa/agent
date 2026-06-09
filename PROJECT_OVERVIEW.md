# Emotion Agent 项目说明文档

## 1. 当前系统是不是在分析历史对话和女生最新回复？

是。

当前网页聊天主链路会读取当前会话的历史消息，并重点分析女生最新发来的内容。系统会结合：

- 最近对话历史
- 女生最新回复
- 你已经确认发出去的话
- 长期记忆，例如姓名、城市、宠物、兴趣、饮食习惯
- 当前关系状态和好感度
- 风险检测结果
- 策略规划结果
- 历史反馈日志，例如复制了哪条、有没有修改、好评还是差评

然后生成多条候选回复，做真人化处理和排序，最后输出最佳回复。

注意：现在系统已经区分了“AI 建议回复”和“你实际发送的回复”。AI 生成后默认只是建议，不会直接当作你已经说过的话。只有你点击网页里的“复制回复”“复制候选”或“记录已发”后，系统才会把那句话作为你真实说过的话写入历史。这样下一轮接话时不会乱接。

## 2. 当前网页主流程

当前真正用于网页聊天的主流程是：

```text
web/app.js
  -> POST /api/chat
chat_server.py
  -> ChatApplication.chat()
  -> ReplyPipeline.run()

ReplyPipeline.run():
  1. ConversationAnalyzer 分析女生最新回复和最近历史
  2. MemoryManager 更新长期记忆和女生画像
  3. RelationshipStateMachine 更新关系阶段和好感度
  4. RiskDetector 做风险检测
  5. StrategyPlanner 决定当前回复策略
  6. ReplyGenerator 生成多条候选回复
  7. Humanizer 做真人化处理
  8. ReplyRanker 打分并选出最佳回复
  9. GrowthSupport 生成社交陪练、机会识别、线下辅助、自信记录
 10. chat_server.py 返回网页
```

## 3. 关键改动位置

如果你要改核心回复效果，优先看这些文件：

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/reply_pipeline.py` | 当前主流水线，串起分析、记忆、状态、策略、生成、真人化、排序 |
| `emotion_agent/analyzers/conversation_analyzer.py` | 分析女生最新回复的情绪、意图、兴趣度、关系阶段、暧昧窗口 |
| `emotion_agent/strategy/strategy_planner.py` | 决定当前应该安抚、继续聊、降温、邀约、推进还是收住 |
| `emotion_agent/generator/reply_generator.py` | 核心回复生成文件，包含 LLM Prompt 和规则兜底回复 |
| `emotion_agent/humanizer/humanizer.py` | 把候选回复变得更像真实微信口吻 |
| `emotion_agent/ranker/reply_ranker.py` | 给候选回复评分，决定最终哪条胜出 |
| `emotion_agent/state/relationship_state_machine.py` | 维护好感度、关系阶段、邀约意愿、边界阻力等 |
| `emotion_agent/memory/memory_manager.py` | 维护长期记忆和女生互动画像 |
| `chat_server.py` | 网页 API 入口、会话管理、真实已发送回复记录 |
| `web/app.js` | 前端聊天交互、复制回复、记录已发、反馈好/不好 |

## 4. 根目录文件说明

| 文件/目录 | 作用 |
| --- | --- |
| `chat_server.py` | 本地网页服务器。提供 `/api/chat`、`/api/feedback`、`/api/reset`、`/api/session_status`。当前网页聊天主要跑这个文件。 |
| `run_agent.py` | 命令行启动入口。可以直接从命令行传聊天内容，让系统生成回复。 |
| `config.yaml` | LLM 配置文件。配置 OpenAI、DeepSeek、Claude、Gemini 的 base_url、model、temperature、max_tokens、system_prompt。 |
| `README.md` | 当前内容很少，只是占位。 |
| `.env` | 本地环境变量文件，通常放 API Key。 |
| `.gitignore` | Git 忽略规则。 |
| `memory.json` | 默认长期记忆文件。 |
| `memory_girl_xiaolin.json` | 某个具体会话对象的长期记忆文件。 |
| `memory_girl_1780913488611.json` | 另一个会话对象的长期记忆文件。 |
| `memory_startup_check.json` | 启动检查或测试用记忆文件。 |
| `server.out.log` | 服务标准输出日志。 |
| `server.err.log` | 服务错误输出日志。 |
| `data/` | 运行时数据目录，保存会话、记忆、反馈日志。 |
| `web/` | 本地网页聊天界面。 |
| `tests/` | 评测集和评测脚本。 |
| `emotion_agent/` | Python 核心代码包。 |

## 5. `emotion_agent/` 核心包说明

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/__init__.py` | 包入口。导出 `ReplyPipeline`，并兼容旧的 `EmotionChatAgent`。 |
| `emotion_agent/__main__.py` | 允许使用 `python -m emotion_agent` 方式启动。 |
| `emotion_agent/main.py` | 旧版组合入口，定义 `EmotionChatAgent`。当前网页主链路不是主要用它，而是用 `ReplyPipeline`。 |
| `emotion_agent/reply_pipeline.py` | 当前最重要的主流程文件。负责把分析器、记忆、状态机、风险检测、策略、生成、真人化、排序串起来。 |
| `emotion_agent/session_store.py` | 会话持久化协调器。负责加载和保存聊天历史、关系状态、每个会话对应的记忆文件路径。 |
| `emotion_agent/sitecustomize.py` | 运行路径辅助文件，用来保证模块直接运行时能正确导入包。 |

## 6. `analyzers/` 分析模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/analyzers/base.py` | 分析器基类接口。 |
| `emotion_agent/analyzers/conversation_analyzer.py` | 当前核心分析器。LLM 优先分析，规则兜底。输出情绪、意图、兴趣度、关系阶段、暧昧窗口等结构化结果。 |
| `emotion_agent/analyzers/risk_detector.py` | 当前主链路使用的风险检测器。判断推进是否过快、是否需要降温、是否有高风险语气。 |
| `emotion_agent/analyzers/emotion_analyzer.py` | 旧版情绪分析器，基于上下文做粗粒度情绪标签。 |
| `emotion_agent/analyzers/intent_analyzer.py` | 旧版意图分析器，做简单意图识别。 |
| `emotion_agent/analyzers/risk_analyzer.py` | 旧版风险分析器。 |
| `emotion_agent/analyzers/__init__.py` | 分析模块导出入口。 |
| `emotion_agent/analyzers/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

## 7. `memory/` 记忆模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/memory/memory_manager.py` | 当前核心长期记忆管理器。负责提取、合并、升级、校验记忆，也维护女生互动画像和用户自信记录。 |
| `emotion_agent/memory/conversation_memory.py` | 旧版会话记忆类，用于保存近期消息。 |
| `emotion_agent/memory/profile_memory.py` | 旧版用户画像记忆。 |
| `emotion_agent/memory/base.py` | 记忆基类接口。 |
| `emotion_agent/memory/__init__.py` | 记忆模块导出入口。 |
| `emotion_agent/memory/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

`MemoryManager` 当前会自动提取或维护：

- 姓名
- 年龄
- 职业
- 城市
- 宠物
- 兴趣
- 生日
- 饮食习惯
- 旅行经历
- 重要事件
- 女生互动画像，例如是否喜欢调侃、是否需要安抚、是否接受清晰安排、边界敏感度
- 用户自信记录，例如做对了哪些沟通动作

## 8. `state/` 状态模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/state/relationship_state_machine.py` | 当前核心关系状态机。维护 L1-L6 关系阶段、好感度 0-100、主动性、回复质量、亲密度、邀约意愿、情绪依赖、边界阻力。 |
| `emotion_agent/state/conversation_state.py` | 旧版会话状态聚合对象。 |
| `emotion_agent/state/emotional_state.py` | 旧版情绪状态对象。 |
| `emotion_agent/state/session_state.py` | 旧版 session 状态对象。 |
| `emotion_agent/state/__init__.py` | 状态模块导出入口。 |
| `emotion_agent/state/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

当前好感度系统主要在 `relationship_state_machine.py` 中。它会根据聊天里的主动性、邀约信号、情绪分享、边界反馈等因素更新分数。

## 9. `strategy/` 策略模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/strategy/strategy_planner.py` | 当前核心策略规划器。决定每一轮回复目标、语气、行动类型、避免事项、候选数量。 |
| `emotion_agent/strategy/growth_support.py` | 社交陪练、机会识别、线下见面辅助、自信建设系统。 |
| `emotion_agent/strategy/strategy_selector.py` | 旧版策略选择器，根据分析结果选策略。 |
| `emotion_agent/strategy/reply_strategy.py` | 旧版回复策略模型或策略定义。 |
| `emotion_agent/strategy/base.py` | 策略基类接口。 |
| `emotion_agent/strategy/__init__.py` | 策略模块导出入口。 |
| `emotion_agent/strategy/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

如果你觉得系统“关系推进太慢”“太像朋友”“太冷”“太油”，一般优先改 `strategy_planner.py` 和 `reply_ranker.py`。

## 10. `generator/` 生成模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/generator/reply_generator.py` | 当前核心回复生成器。优先调用 LLM 生成候选回复，LLM 不可用时走规则兜底。这里的 Prompt 最影响回复风格。 |
| `emotion_agent/generator/response_generator.py` | 旧版生成器，给 `EmotionChatAgent` 兼容链路用。 |
| `emotion_agent/generator/base.py` | 生成器基类接口。 |
| `emotion_agent/generator/__init__.py` | 生成模块导出入口。 |
| `emotion_agent/generator/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

如果要改“AI 味重不重”“像不像微信真人”“要不要更短”，主要改 `reply_generator.py`。

## 11. `humanizer/` 真人化模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/humanizer/humanizer.py` | 当前主链路真人化处理。对候选回复做口语化、短句化、去模板化。 |
| `emotion_agent/humanizer/response_humanizer.py` | 旧版真人化模块，给兼容链路使用。 |
| `emotion_agent/humanizer/base.py` | 真人化基类接口。 |
| `emotion_agent/humanizer/__init__.py` | 真人化模块导出入口。 |
| `emotion_agent/humanizer/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

## 12. `ranker/` 排序模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/ranker/reply_ranker.py` | 当前核心排序器。按自然度、微信感、风险控制、情绪价值、关系推进、画像匹配等维度给候选回复打分。 |
| `emotion_agent/ranker/response_ranker.py` | 旧版排序器，给兼容链路使用。 |
| `emotion_agent/ranker/base.py` | 排序器基类接口。 |
| `emotion_agent/ranker/__init__.py` | 排序模块导出入口。 |
| `emotion_agent/ranker/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

如果候选里有好回复但最终没选中，优先改 `reply_ranker.py`。

## 13. `providers/` 模型供应商模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/providers/base.py` | LLM 基类 `BaseLLM`。统一 `generate()`、`analyze()`、`score()` 接口，统一返回响应对象，并处理超时、认证失败、网络异常。 |
| `emotion_agent/providers/openai_provider.py` | OpenAI 兼容接口 Provider。 |
| `emotion_agent/providers/deepseek_provider.py` | DeepSeek Provider。 |
| `emotion_agent/providers/claude_provider.py` | Claude Provider。 |
| `emotion_agent/providers/gemini_provider.py` | Gemini Provider。 |
| `emotion_agent/providers/config_loader.py` | 读取 `config.yaml` 和 `.env` 中的 API 配置。 |
| `emotion_agent/providers/provider_factory.py` | 旧版 Provider 工厂。 |
| `emotion_agent/providers/__init__.py` | Provider 模块导出入口。 |
| `emotion_agent/providers/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

以后换模型时，理论上只需要换 Provider，例如：

```python
from emotion_agent.providers import DeepSeekProvider

provider = DeepSeekProvider()
```

## 14. `storage/` 存储模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/storage/file_storage.py` | 当前会话文件存储。把每个会话的 messages 和 state 存到 `data/sessions/*.json`。 |
| `emotion_agent/storage/interaction_logger.py` | 当前反馈日志存储。记录生成、复制、选择、编辑、好评、差评、女生后续回复。 |
| `emotion_agent/storage/memory_storage.py` | 内存版存储，适合测试或临时运行。 |
| `emotion_agent/storage/session_manager.py` | 旧版 session 存储管理器，给 `EmotionChatAgent` 兼容链路使用。 |
| `emotion_agent/storage/base.py` | 存储基类接口。 |
| `emotion_agent/storage/__init__.py` | 存储模块导出入口。 |
| `emotion_agent/storage/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

当前重要数据位置：

- 会话历史和状态：`data/sessions/*.json`
- 每个对象的长期记忆：`data/memory/*.json`
- 反馈日志：`data/interaction_logs/*.jsonl`

## 15. `utils/` 工具模块

| 文件 | 作用 |
| --- | --- |
| `emotion_agent/utils/types.py` | 全局共享类型，例如 `Message`、`ProviderName`、`LLMResponse`、`GenerationResult`。 |
| `emotion_agent/utils/config.py` | Agent 配置模型。 |
| `emotion_agent/utils/exceptions.py` | 项目异常类型。 |
| `emotion_agent/utils/logger.py` | 日志工具。 |
| `emotion_agent/utils/__init__.py` | 工具模块导出入口。 |
| `emotion_agent/utils/sitecustomize.py` | 子目录直接运行时的导入辅助。 |

## 16. `web/` 网页界面

| 文件 | 作用 |
| --- | --- |
| `web/index.html` | 网页结构。包含聊天区、状态面板、候选回复、机会识别、社交陪练、线下辅助、自信记录等区域。 |
| `web/app.js` | 网页核心交互。发送消息、渲染回复、复制回复、记录已发、反馈好/不好、切换不同女生会话。 |
| `web/styles.css` | 网页样式。控制布局、聊天气泡、按钮、侧边栏、候选回复等视觉效果。 |

## 17. `tests/` 测试与评测

| 文件 | 作用 |
| --- | --- |
| `tests/run_eval.py` | 自动评测脚本。加载测试用例并跑完整 `ReplyPipeline`，检查意图、风险、好感度范围、回复长度等。 |
| `tests/fixtures/chat_eval_cases.json` | 手写评测样本。 |

当前 100 条评测主要是合成回归测试，不等于真实线上数据质量。它能证明系统稳定性，但不能完全证明真实聊天效果。

## 18. 当前系统已经能满足的需求

- 本地网页聊天辅助
- 多女生独立会话
- 每个对象独立长期记忆
- 读取历史对话和女生最新回复
- 区分 AI 建议回复与真实已发送回复
- LLM 优先分析，规则兜底
- 多模型 Provider 结构
- 好感度和关系阶段维护
- 回复候选生成
- 真人化处理
- 多维度评分选最佳
- 机会识别
- 社交陪练解释
- 线下见面辅助
- 自信建设记录
- 用户反馈日志

## 19. 当前还建议补充优化的点

1. 增加“手动补录历史”功能  
   方便把微信里已经聊过的内容一次性导入，让系统更快接上上下文。

2. 增加“历史摘要”功能  
   现在主要看最近窗口。长期聊天多了以后，需要把早期重要话题压缩成摘要，避免超过上下文。

3. 增加 Provider 状态检测接口  
   明确显示当前是否真的调用 DeepSeek、使用哪个模型、最近一次 API 是否成功。

4. 把反馈日志反哺排序器  
   现在已经记录复制、修改、好/不好，但还可以进一步让 `ReplyRanker` 学会偏向高复制率、高好评率、少修改的回复风格。

5. 建立真实授权评测集  
   当前 100 条主要是合成样本。上线前应该建立真实、匿名、授权的聊天样本评测集。

6. 检查并修复中文编码问题  
   部分文件在终端里出现过乱码显示。如果文件本身有 mojibake，会影响关键词规则和 Prompt 质量，需要统一为 UTF-8。

## 20. 一句话总结

当前系统的本质是一个“基于历史上下文、长期记忆、关系状态和 LLM 分析的微信回复辅助系统”。它不是只看女生当前一句话，而是会结合整段会话里她说过什么、你确认发过什么、她的画像、当前好感度和风险状态，再生成更贴合当下关系阶段的回复。
