# Creation：众神创作工作台

Creation 是《优秀情侣奖》的本地多智能体创作工具，也可独立生成恋爱故事。本文按 2026-11-16 当前代码核对：前期四阶段 + author v2 后期五阶段，共九阶段。故事日历使用 2025 年，与实际运行日志日期分开。

## 1. 范围与游戏端的区别

| 模式 | 产出与停止位置 |
| --- | --- |
| 纯恋爱，不勾选“对接颁奖” | 人物、关系、细节及个人接管包，前四阶段审定后结束 |
| 对接颁奖 | 继续报名剧情、正式报名表；由玩家确认入围后，生成披露、答辩剧本和读稿态度 |

这是离线作者工作台，不是校园社会模拟，也不是现场自由答辩系统。示例模式使用固定响应，不代表真实模型质量。

当前游戏入口见 `branches/latest/README.md`：仅优秀情侣奖，少年奖路线已删除；游戏完成筹备会议 → 通知 → 双人报名审阅 → 玩家入围 → 双人答辩 → 结束，没有评分、获奖决定或颁奖。工作台按钮仍沿用“对接颁奖”的名称，不表示游戏已实现颁奖。作者公告包含5月10日现场颁奖的故事安排，也不等于游戏已有该功能。

目前不是导出后自动实时接入游戏；游戏使用明确源包的本地白名单提取结果。准备稿不等于现场答辩记录，未来自由答辩、学生自由发挥且无 Critic 的设想尚未在此实现。

## 2. 启动与配置

在项目根目录 `D:/gamestuff/model-couple` 执行：

```bash
python tools/creation/student_server.py --port 8765
```

也可使用本机已配置的 Python：

```bash
"C:/Users/25367/AppData/Local/Programs/Python/Python314/python.exe" "D:/gamestuff/model-couple/tools/creation/student_server.py" --port 8765
```

浏览器打开 **http://127.0.0.1:8765/creation/**。后端使用 Python 3 标准库，无需数据库、Concordia 或前端构建。不能双击 HTML 代替 HTTP 入口。端口占用时先确认已有服务版本，不重复启动、不擅自终止进程。后端修改需重启，前端修改需刷新；刷新前导出工程。

唯一共享 API 配置为 `tools/common/config.json`，由页面配置区保存；不再修改旧 `creation/config.json`。合法旧配置仅在目标不存在时迁移，不覆盖已有目标。配置包含明文密钥，不作为静态文件公开，不应出现在截图、演示或公开仓库。真实模式需要兼容聊天补全接口、模型和 API_KEY；示例模式无需密钥。执行真实模式的一步／阶段／自动可能计费，导入或创建暂停工程本身不自动调用模型。

## 3. 九阶段职责（author v2）

| 阶段 | 作者 | 审查者 | 职责与边界 |
| --- | --- | --- | --- |
| 1 人物 | Prometheus | C_Prometheus | 独立学生身份、学业、生活、表达与荣格八维倾向 |
| 2 框架 | Cupid | C_Cupid | 配对、吸引基础、连续关系年表及关键因果 |
| 3 细节 | Aphrodite | C_Aphrodite | 分阶段事件、长期习惯和逐人观察，不回修已审框架 |
| 4 记忆 | Mnemosyne | C_Mnemosyne | 按本人可知资料生成角色指令、记忆和私有接管包 |
| 5 报名剧情 | Chronos | C_Chronos | 只写4月24日至5月4日生活、报名过程和态度；不写报名表或正文；结局必须双方同意并报名 |
| 6 正式报名表 | Muse | C_Muse | 独立填表任务，承接 Chronos；双方第一人称面向评委的正式自我陈述，授权隐私放 metadata |
| 7 本人披露 | Icelos | C_Icelos | 本人选择愿意提供给答辩 Muse 的材料，可以为空，不泄露隐瞒秘密 |
| 8 答辩剧本 | Muse | C_Muse | 使用与填表不同的提示词，包装公开履历及已披露信息，准备双人陈述、展示与问答衔接 |
| 9 读稿态度 | Icelos | C_Icelos | 对具体台词／动作的喜欢、反感、理由和配合心态；不改剧本、不触发 Muse 返工 |

Chronos 可写犹豫、争执和协调，但新契约不接受不报名、partial、未提交或撤回终局。结构为逐人 `experiences/attitude/consent=true` 和 `registration.status=submitted/submitted_on`，没有旧 form 字段。正式表锁定后才生成游戏报名快照；披露及以后仍由玩家外部入围事件门控，模型不能代选。

填表 Muse 使用公开履历、个人实践和 Chronos 剧情，只写有依据的个人学业、专业实践、成长、关系支持及参评理由，未知不补造学校、成绩、排名、奖项或项目；不是只写共同恋爱经历。`metadata` 单独保存双方授权、隐私和提交日期，不把政策说明念进正文。填表 Critic 检查履历来源与学段，不适用答辩舞台虚构豁免。

答辩 Muse 直接以真实姓名自然说话，体现人物差异、具体接话和互动，不念 s3/s4、来源编号、“展示句”或授权隐私流程口号。结构中的人物标识仍使用 ID。说话风格 `voice` 只能由 Icelos 自愿披露，不直接把混合人物资料交给教师。

允许指导教师为宣传夸张、改写甚至编造舞台情节；`source_refs` 表示素材启发而非事实证明，`fact/interpretation/staging` 是兼容标签，不要求逐字匹配。加工必须服务答辩，不能写回真实履历、Chronos 经历、个人记忆或报名快照，也不能新增实际入围、获奖结果。C_Muse 在剧本阶段只审表达、分工、节奏、展示、结构、素材入口、秘密与外部事件边界，不作真实性审查，不给情侣评分、不设权重或算法选优；approved 只表示稿件可用，不是情侣评价或获奖推荐。其他阶段仍审事实依据和个人知识边界。

作者输出由独立 Critic 审查后锁定，失败保留意见再修订；默认持续修订不保证收敛，也不代表免费。程序只保证相应结构、日期、来源与锁定校验，不能保证语义绝对一致。荣格八维是创作参数，不是诊断或测评结论。

### 人物、排名与秘密隔离

Prometheus 自主取名，不把示例姓名当固定名单。C_Prometheus 可提出有依据的改名意见，由作者在人物审定前落实；人物 ID、性别、年龄、专业及年级不变，issue 按 ID 定位。审定后姓名锁定。

排名由 `runtime.py → extracted_rank` 优先取已有 `grade_rank`，否则从 `grades` 原文提取明确的专业／年级排名；没有就标“待补充”，绝不把绩点换算成排名。当前苏晚棠为**本科专业前5%**，不是研究生排名；郑亦航为**本科年级排名中游**。绩点和排名分列，保留原文及学段含义；该提取器是有限文本规则，不是通用学段推断器，新增素材仍须核对。

共同事件按逐人 `observation` 授权，`interpretation` 只是本人理解。Mnemosyne 不继承未获知视角；不能将“你不知道的秘密是……”写进角色上下文。

答辩公开履历投影仅白名单 `name/major/year/grades`，引用为 `profile.<sid>.<field>`。不猜学校，不从 `background/independent_life` 自动提取经历；个人实践须经本人披露才进入答辩素材。教师不直接获取整份 cognition、私有接管包、记忆、秘密或作者审计记录。本人及其披露审查者可读本人秘密以检查边界，不可输出秘密原文。

Icelos 新披露项仅 `id/text/source_refs`，正文逐字摘录非 `private_information` 来源，全部已披露内容均可用。个人披露可为空；双方披露为空但有公开履历仍可继续。只有公开履历和披露均无来源才返回 `no_disclosed_material`，不调用模型、不增加 calls，不是授权不足。

Muse 只引用 `allowed_source_refs`，`context_only_refs` 不可作为新素材入口。报名正文仅作上下文；只有整篇以 `own.form_text` 逐字披露才提供 `application.<sid>` 引用，片段披露不授权整篇。每段 `source_refs` 必须为非空字符串数组；`backstage` 是字符串数组，可为 `[]`，不强转无效类型。

## 4. 提示词与校园配置

主线作者、Critic、修订规则和示例结构集中在 `tools/creation/prompts.json`，不含密钥。动态上下文、状态机、白名单和实质校验仍在代码；修改提示词不能放宽代码契约。只编辑文本，不随意增删 schema 字段、改类型或枚举。

| 精确位置 | 用途 |
| --- | --- |
| `foundry.templates.calendar/default_brief/campus_context` | 前期日历、默认要求及校园包装 |
| `foundry.templates.buildPrompt_*` | 人物／关系／细节作者与审查及修订 |
| `foundry.templates.cupidPrompt_*/cupidTask_*` | 关系年表、分阶段事件／习惯与任务说明 |
| `foundry.templates.takeoverPrompt_*` | Mnemosyne 与其 Critic 的私有接管编译 |
| `foundry.templates.prompt_0/prompt_1/prompt_2` | 对接／纯恋爱套件与失败反馈 |
| `author.templates.rule_3/rule_0/rule_7` | 后期共同身份前后缀与 JSON 结构连接 |
| `author.templates.rule_1` | Chronos 报名剧情 |
| `author.templates.application_writer/application_critic` | 正式填表 Muse 与独立审查专用规则 |
| `author.templates.rule_4/rule_5/rule_6` | Icelos 披露／Muse 答辩／Icelos 读稿态度 |
| `author.templates.rule_2` | 除填表专用审查外的后期 Critic 规则及剧本例外 |
| `foundry.schemas/author.schemas` | 模型输出示例结构，包括独立 `APPLICATION_SCHEMA` |

前期 `{{p0}}` 等占位符按 `student-foundry.html` 的 `renderPrompt` 实参使用；集合由 `prompt_catalog.py` 校验，不能改名、增删，不执行表达式或递归替换。后期模板直接拼接，无占位符。目录校验重复键、危险键、必需键、类型和占位符契约；失败明确报错，不退回硬编码或求值 JSON。

前端通过 `/creation/prompts.js` 同步加载快照，作者每次组装 messages 重新读取目录。保存提示词后建议重启服务并刷新页面，先导出工程；已有页面或在途调用不会自动采用新文本。`runtime.py` 的 legacy 聊天提示词不在该外置范围。

校园配置支持粘贴 JSON 或导入 UTF-8 `.json`（最大256 KiB、序列化后60000字符），参考 `documents/校园配置提示词_顶尖综合研究型大学.json`。必须且只能有 `common/prometheus/cupid/aphrodite` 四个字符串字段，可为空；非法 JSON、字段、UTF-8、大小或时间边界拒绝且保留输入。旧 Markdown 仅供历史参考。

新建时冻结到 `creation.state.config.campusPrompt`（独立工程为 `state.config.campusPrompt`）；输入框后改不影响现有工程。前三阶段作者／Critic／修订分别注入 common + 当前阶段字段，后续不直接接收校园原文。旧缺字段迁为空配置，旧字符串迁至 common；工程脱敏逻辑仍可能替换敏感样式正文。校园正文不是 API 配置，不直接进入运行设定或个人接管包。

## 5. 日历、运行与恢复

| 故事日期 | 事项 |
| --- | --- |
| 2025-04-23 周三 | 前期自然生活设定截止 |
| 2025-04-24 周四 | 公告发布、报名开放 |
| 2025-05-04 周日 | 报名截止，Chronos 必须完成报名结局 |
| 2025-05-05 周一 | 玩家决定并发布入围，之后准备链可继续 |
| 2025-05-10 周六 | 答辩日；当前游戏只做到答辩结束 |

推荐演示：示例模式 → 按需勾选对接 → 新建并进行一步 → 完成阶段／自动 → Chronos 剧情 → 独立 Muse 正式表 → 停在玩家入围门槛 → 明确录入入围决定 → 披露／答辩／态度 → 导出并验证暂停恢复。不要称示例跑通为真实模型质量通过。

统一工作区保持三栏：配置控制、对话轨迹、九阶段档案。导航与人物筛选只改变查看，不改变运行目标；日志是两个原生引擎的只读投影，不复制或互写业务状态。任务统计合计两个引擎，API 请求只统计已有证据，不推算旧历史。后期一次只处理选定的一对情侣，不自动批量运行所有情侣。

- 一步执行一个作者／审查任务；阶段执行至当前阶段通过；自动会停在玩家入围门槛。
- 暂停阻止后续调度，不保证取消在途付费请求；停止后先“恢复执行权限”，再显式执行。
- 前期上游等待默认300秒，网页总等待多30秒。自动失败重试默认关闭，默认额外2次；临时网络和结构错误可按配置重试，不降低校验。超时不保证上游停止，重试可能重复计费。
- 前四阶段已完成但纯恋爱未对接时，选择情侣后点“启用颁奖对接 / 进入Chronos”并确认；只创建暂停工程，不自动执行。单改勾选不等于创建工程。
- 导入恢复为暂停，不自动付费；刷新前导出完整工程，不能仅靠运行设定恢复进度。

### 版本兼容与披露重规划

统一外壳仍为 `model-couple-unified-project-v1`，前期工程和运行设定有相应导入入口；**后期只接受 `model-couple-author-project-v2`**。旧 author v1 明确报版本错误，不静默迁移、不补造独立填表审查；保留旧原档，需要新建 v2 按新契约继续。统一外壳版本未变不代表内嵌旧 author 可直接续跑。

v2 校验仍允许历史披露保留完整 `teacher_knows/may_write/may_perform` 三布尔字段，不改原 JSON 或摘要，但忽略其业务值；新生成不能再输出这些字段。这不是旧 author v1 的迁移入口。旧授权及逐字事实台词错误保留历史，但不再作为失败反馈注入；历史 C_Muse 的真实性要求由当前剧本规则覆盖，其他有效边界意见仍须处理。

“重新规划披露 / 补充披露”调用 `POST /api/author/replan_disclosure`，参数 `{"project_id":"…","confirmed":true}`。须已入围、无在途请求且尚无 script/attitude 结果或锁定；停止后先恢复执行权限。动作自身零模型调用并保持暂停，从两人披露重新开始，保留 Chronos、报名快照及玩家入围绑定。旧披露、草稿、失败及对应 versions/reviews 归档到 `logs` 的 `disclosure_replanned.detail`，不再作为当前素材或旧批准复用，也不提供给 Muse。归档日志不是玩家公开内容，原用户文件不覆盖。

## 6. 文件、人工修订与游戏提取

| 文件／协议 | 用途 |
| --- | --- |
| 统一工程 `model-couple-unified-project-v1` | 前后状态及关联，完整续写备份；内嵌作者须符合 v2 |
| 作者工程 `model-couple-author-project-v2` | 后期五阶段结果、锁、审查和日志 |
| 运行设定 `model-couple-runtime-v1` | 已审定人物、关系、个人接管包；不是完整工程 |
| 游戏报名包 `model-couple-game-package-v1` | 正式表锁定后形成的已提交快照 |
| 答辩准备包 `model-couple-preparation-package-v1` | 剧本、个人态度与所需记忆；不是现场记录 |

`player_visible/role_private` 只是逻辑分区，不是加密。持有完整包的人能读私有信息，消费者必须按人隔离，不能整包塞入学生上下文或浏览器。

当前 `tools/common/successful-run.json` 有人工修订：`author.manual_revision.actor=operator`、`model_reviewed=false`，附修订阶段摘要及原因；`manual_revision.original_author` 完整保留原 author 和历史审查，原始人物保留。历史 reviews 不改、不新增伪造批准。当前结构校验通过不等于新正文／剧本经模型复审，不可宣传为“重新生成并通过模型审查”。`revise_public_result.py` 是该次明确授权的一次性修订脚本，拒绝重复覆盖，不应作为常规启动命令运行。该脚本仍指向旧 `tools/successful-run.json`；当前原档实际位于 `tools/common/successful-run.json`，不要为运行旧脚本复制或覆盖历史原档。

游戏端 `scripts/extract-couple.mjs` 的唯一位置参数是**源 JSON 路径**，不是输出路径；输出固定为 `branches/latest/src/coupleCandidates.js`。从项目根目录执行的准确命令见游戏 README。它只选公开报名字段及 script 中 dialogue/chorus 发言，不提取动作、后台、source_refs、私有包、审查或 nomination；不会自动给未知信息补履历。本次文档更新不执行提取，不改源包或前端产物。

主要实现：`student_server.py` 为服务入口；`student-foundry.html` 为前期引擎；`unified.js` 为九阶段装配和工程关联；`author-panel.html/author.py` 为后期 UI／引擎；`runtime.py` 为设定及游戏包校验与旧协议；`prompt_catalog.py` 为提示词契约。数据在 `logs/`、`data/author_projects/` 和旧 `data/sessions/`，不要当垃圾清除。旧 `/simulation/` 跳转统一入口，不是当前运行主线。

## 7. 开发者验证（不调用真实模型）

以下命令均从项目根目录执行，脚本实际存在；Python 需能在命令行使用。按范围选择，不把执行过旧契约测试当作当前版本已通过。

```bash
python -m unittest discover -s tools/creation -p "test_author.py" -v
python -m unittest discover -s tools/creation -p "test_prompt_catalog.py" -v
node tools/creation/test_prompt_catalog.cjs
node tools/creation/test_student_foundry.cjs
node tools/creation/test_creation_retry.cjs
node tools/creation/test_author_page.cjs
node tools/creation/test_unified.cjs
node tools/creation/test_unified_integration.cjs
```

完整 Python 检查入口为 `python -m unittest discover -s tools/creation -p "test_*.py" -v`，包含旧 runtime／服务兼容测试；本次是否运行及结果以工作日志为准。`test_unified.cjs` 会只读 `tools/creation-unified-project.json` 作真实前期导入验证；本次该文件缺失，实跑报 ENOENT，未通过，未补造或复制 fixture。DOM/VM 测试不等于浏览器视觉验收。

历史 `test_creation_project.cjs` 另依赖 `logs/2026-11-15_09-49-14_023086_dfed95d047b441d7b2193874c697ef6d.log`，缺失会失败，不能伪造 fixture、绕过或声称通过；带 `--write-recovery` 会写恢复产物，不属于普通只读检查。游戏单奖项、共享时钟、后端与独立浏览器测试见 `branches/latest/README.md`。本文不要求构建、打包、发布、真实报名或付费模型调用。
