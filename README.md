# Creation：众神创作工作台

Creation 是《优秀情侣奖》的本地多智能体创作工具。它将学生人设、恋爱历史、个人记忆、报名经历、报名表及双人答辩剧本组织为可审查、可恢复、可导出的创作流程。

它也可以独立作为恋爱故事生成器使用。本文依据 2026-11-16 的代码状态编写；故事内日历使用 2025 年，与实际运行日志时间分开。

## 1. 先看懂它做什么

| 模式 | 产出 | 结束位置 |
| --- | --- | --- |
| 纯恋爱，不勾选“对接颁奖” | 学生、关系框架、具体经历、个人接管包 | 前四阶段审定后结束 |
| 对接颁奖 | 上述设定，以及报名经历、报名正文、披露包、答辩剧本、个人态度 | 经过玩家入围决定后，完成准备链 |

这是**离线创作工具**，不是正在运行的校园社会模拟。模型扮演作者与审查者，结果供游戏使用。示例模式是固定示例，不代表真实模型创作效果。

现场答辩的设想是：两名学生拿到背景、剧本和本人态度后自由回应玩家，不出现任何Critic。但本工具目前只做到答辩准备包，尚未实现该现场系统。

## 2. 启动与配置

### 环境

- Python 3，后端使用标准库，无需为此安装数据库或Concordia。
- 浏览器；必须经本地HTTP服务打开，不能双击HTML代替。
- 真实生成需要兼容聊天补全接口的服务、模型和API_KEY。示例演示不需要密钥。

本项目当前使用的Python：

```bash
"C:/Users/25367/AppData/Local/Programs/Python/Python314/python.exe" "D:/gamestuff/model-couple/tools/creation/student_server.py" --port 8765
```

在项目根目录，也可使用已配置好的Python：

```bash
python tools/creation/student_server.py --port 8765
```

打开：**http://127.0.0.1:8765/creation/**

服务仅监听本机。8765被占用时，先确认已有进程属于哪个版本，不要反复启动多个服务。修改Python后端后需要重启；修改前端后需要刷新。刷新前导出工程。

### 统一API配置

权威配置文件为：`tools/common/config.json`。

在页面API配置区填写接口地址、API_KEY、模型名称并保存。creation设置与后续作者流程共用该文件；不要继续修改旧的`creation/config.json`副本。目标配置不存在时，服务支持从合法旧配置安全迁移；已有目标不会被覆盖。

**密钥以明文保存。不要把配置文件放进演示材料、截图或公开仓库。** 配置通过同源服务读取，不作为静态文件公开。切换示例／真实模式时先检查当前模式，避免误调用。

### 主线提示词：只编辑 `prompts.json`

主线八阶段的模型规则与输出示例 schema 集中在 `tools/creation/prompts.json`；不包含 API 地址或密钥。

| 文件／目录键 | 用途 |
| --- | --- |
| `prompts.json → foundry.templates.calendar` | 前四阶段共同日历规则 |
| `foundry.templates.cupidPrompt_*` | Cupid框架、Aphrodite分阶段事件／习惯初稿及数量规则 |
| `foundry.templates.takeoverPrompt_*` | Mnemosyne作者与审查者、私有接管输出说明 |
| `foundry.templates.buildPrompt_*` | 人物初稿／修订、人物／关系／细节审查、框架／细节修订规则 |
| `foundry.templates.prompt_0 / prompt_1 / prompt_2` | 对接套件、纯恋爱套件、失败重试纠错追加 |
| `foundry.schemas` | 人物、八维、关系、观察、事件、习惯、年表、审查及接管包示例结构 |
| `author.templates.rule_0 / rule_3 / rule_7` | 后四阶段共同身份后缀／前缀与JSON结构连接文本 |
| `author.templates.rule_1 / rule_4 / rule_5 / rule_6 / rule_2` | Chronos、首次Icelos、Muse、第二次Icelos、共同Critic规则 |
| `author.schemas` | 后四阶段与共同Critic的输出示例结构 |
| `prompt_catalog.py` | 固定位置安全读取、重复键／危险键／必需键／结构类型／占位符契约校验 |
| `student_server.py → /creation/prompts.js` | 每次请求读取同一JSON，生成同步bootstrap脚本 |
| `student-foundry.html` / `author.py` | 保留动态上下文组装、状态机、数据隔离和实质校验 |

修改方法：先备份工程，在JSON中按规则原文搜索对应条目，只修改字符串文本，保存为UTF-8合法JSON。无需改JS／Python即可调整模型措辞。schema是**示例结构**而非可自由更改的接口定义：可改说明文字，不要增删字段或改值类型；不要把代码要求的枚举值改成其他词。强制的日期、ID、数量、知识隔离、白名单、授权、审查通过条件和阶段锁定仍由代码校验，不会因改提示词而放宽。

模板中的 `{{p0}}`、`{{p1}}` 等是显式参数，不是JS表达式。每个条目的占位符集合固定；可调整位置或重复使用，但不要改名、增加或删除占位符。对应参数以 `student-foundry.html` 内 `renderPrompt('条目名', {p0: ..., p1: ...})` 为准，例如 `cupidPrompt_0.p0` 为情侣对数，`cupidPrompt_4.p0/p1/p2/p3/p4/p5` 分别为角色、日历、细节阶段边界、当前规则、细节档位、序列化schema。替换只执行一遍；参数中出现的模板语法也只是数据，不会递归替换，不使用 `eval` 或动态函数。

前端在原inline脚本之前通过普通同步 `<script src="/creation/prompts.js">` 加载目录，VM测试直接注入同份JSON。作者每次生成 `messages` 都重新读取文件；路由每次请求也重新读取，均不缓存。**建议修改后重启服务并刷新页面**（刷新前导出工程）；已有页面继续使用加载时快照，不会自动热更新，进行中的请求也不会改写。

缺文件、坏JSON、重复键、缺键、类型或占位符不合约时明确失败，不回退到旧硬编码提示词。加载路由返回设置 `CREATION_PROMPTS_ERROR` 的JavaScript，页面运行控制区显示具体错误并禁用执行；修复 `prompts.json` 后刷新即可重新加载。作者调用会记录失败并保留未提交步骤。所有加载均不求值JSON内容。

### 角色与精确模板键／参数映射

下表前四阶段的键均位于 `foundry.templates`。不带参数说明的键不接受占位符；保留现有数字键以避免无关重构。

| 角色／用途 | 精确键 | 参数含义（按p0、p1…顺序） |
| --- | --- | --- |
| 所有前期角色 | `calendar` | 无；共同日历 |
| 页面初始创作要求 | `default_brief` | 无；仅初始化空输入，不覆盖用户输入或导入工程 |
| 本人接管边界 | `takeover_boundary_confirmation`、`takeover_boundary_unknown` | 无；进入visible_material.boundary的授权说明与未知边界，字段白名单仍由代码强制 |
| Prometheus初稿／修订、C_Prometheus及C_Cupid基础 | `buildPrompt_4` | p0角色；p1日历；p2用户brief；p3输出schema JSON |
| Prometheus附加规则 | `buildPrompt_5` | p0学生人数 |
| Cupid通用关系附加规则 | `buildPrompt_6` | p0情侣对数；实际框架初稿走下列分层分支 |
| C_Prometheus | `buildPrompt_7` | 无；人物审查专用 |
| C_Cupid | `buildPrompt_8` | 无；框架审查专用 |
| 通用人物／框架Critic | `buildPrompt_9`、`buildPrompt_13`、`buildPrompt_14` | 无；审查原则、目标枚举前后缀 |
| 通用Critic目标标签 | `buildPrompt_10`、`buildPrompt_11`、`buildPrompt_12` | 无；分别为人物分支“全部人物”、关系分支“全部人物”、“全部情侣” |
| Cupid框架初稿 | `cupidPrompt_0` | p0情侣对数 |
| Aphrodite事件／习惯初稿 | `cupidPrompt_1` | p0情侣ID；p1阶段ID；p2层events/habits；p3数量规则；p4情侣ID；p5阶段ID（末两项构成条目ID前缀） |
| Aphrodite数量规则 | `cupidPrompt_2`、`cupidPrompt_3` | p0分别为事件数量、习惯数量 |
| Cupid／Aphrodite分层共同外壳 | `cupidPrompt_4` | p0角色；p1日历；p2细节阶段边界；p3当前层规则；p4输出档位；p5输出schema JSON |
| Aphrodite阶段边界 | `cupidPrompt_5` | 无；只做细节 |
| 分层任务／输出说明 | `cupidTask_0`、`cupidTask_1`、`cupidTask_2`、`cupidTask_3` | 仅cupidTask_1接受p0层名、p1情侣ID、p2阶段ID；其余无参数 |
| C_Aphrodite细节审查 | `buildPrompt_0` | p0日历；p1审查schema JSON |
| Aphrodite逐对修订 | `buildPrompt_1` | p0日历；p1含完整story的单对输出schema JSON |
| Cupid逐对框架修订 | `buildPrompt_2` | p0日历；p1含完整story的单对输出schema JSON |
| 上下文校验标签 | `buildPrompt_3`、`buildPrompt_15` | 无；分别为Cupid分层、通用待发送上下文 |
| Mnemosyne／C_Mnemosyne共同外壳 | `takeoverPrompt_0` | p0角色；p1当前学生ID；p2日历；p3作者或Critic规则；p4输出schema JSON |
| Mnemosyne作者、C_Mnemosyne审查 | `takeoverPrompt_1`、`takeoverPrompt_2` | 无；分别为作者与审查规则 |
| 接管输出／审查示例说明 | `takeoverPrompt_3`至`takeoverPrompt_7` | 无；依次为本人记忆、私有信息、严重度、问题、建议示例 |
| 接管上下文校验标签 | `takeoverPrompt_8` | 无 |
| 所有前期messages追加 | `prompt_0`、`prompt_1`、`prompt_2` | 无；分别为对接、纯恋爱、失败纠错前缀 |

后四阶段的键均位于 `author.templates`，直接拼接字符串，**全部无占位符**：

| 角色／用途 | 精确键 |
| --- | --- |
| 所有作者与Critic共同身份 | `rule_3`（角色名前缀）、`rule_0`（角色名后共同规则）、`rule_7`（输出schema连接文本） |
| Chronos／C_Chronos报名期 | `rule_1` |
| Icelos／C_Icelos首次披露 | `rule_4` |
| Muse／C_Muse剧本 | `rule_5` |
| Icelos／C_Icelos第二次态度 | `rule_6` |
| 所有后期Critic额外规则 | `rule_2`（在当前阶段规则之后追加） |

范围：覆盖主线所有作者与Critic、初稿／修订分支、默认brief、接管边界说明、套件追加、重试纠错及模型schema说明。仍在代码中的是动态数据、来源投影／边界字段白名单、公告与游戏业务常量、程序校验错误、UI文案和固定demo响应；这些不是可自由编辑的模型规则模板。`runtime.py` 的legacy旧聊天模型提示词不在本次外置范围。

离线检查（不调用真实模型）：

```bash
python -m unittest discover -s tools/creation -p "test*.py" -v
node tools/creation/test_prompt_catalog.cjs
node tools/creation/test_student_foundry.cjs
node tools/creation/test_creation_retry.cjs
node tools/creation/test_creation_project.cjs
node tools/creation/test_unified.cjs
```

## 3. 第一次演示：推荐路线

1. 启动服务，打开统一creation入口。
2. 选择“示例”模式。若要演示完整流程，勾选“对接颁奖”。
3. 设置学生数量、情侣数量和细节档位。首次讲解建议小规模，避免把观众注意力淹没在长文本中。
4. 点“进行一步”，观察角色任务、审查意见和结果档案。
5. 点“完成当前阶段”，展示创作与审查如何交替。
6. 点“全自动至结束”，完成前期并交接Chronos。后续处理选定的一对情侣，不自动批量运行所有情侣。
7. 查看4月24日至5月4日经历、是否填写、填写日期、提交状态与正文。
8. 到入围门槛时暂停。明确录入“玩家已决定入围”后，继续披露、剧本与态度阶段。
9. 展示已提交报名包、准备包与统一工程导出。说明三者用途不同。
10. 导入工程，确认暂停恢复且不自动调用模型。

正式测试时再切换真实API。不要把“示例流程跑通”说成“真实模型质量已验证”。

## 4. 八阶段如何工作

| 阶段 | 作者 | 审查者 | 职责边界 |
| --- | --- | --- | --- |
| 1 人物 | Prometheus | C_Prometheus | 创造独立学生：身份、学业、目标、矛盾、表达与荣格八维倾向 |
| 2 框架 | Cupid | C_Cupid | 牵线配对，确定吸引基础、关系阶段及关键因果 |
| 3 细节 | Aphrodite | C_Aphrodite | 分阶段填充具体事件、长期习惯、逐人观察，不回退修改已审框架 |
| 4 记忆 | Mnemosyne | C_Mnemosyne | 按个人可知资料编译角色指令、记忆、私人信息和披露边界 |
| 5 报名期 | Chronos | C_Chronos | 编写公告后至截止日前的经历、参评态度、填表行为及正文 |
| 6 披露 | Icelos | C_Icelos | 逐人决定告诉教师什么、哪些能写进稿件、哪些能上台表演 |
| 7 剧本 | Muse | C_Muse | 基于获准材料写双人JSON表演剧本，保留教师包装和功利倾向 |
| 8 态度 | Icelos | C_Icelos | 写出双方对具体段落的喜恶与准备执行的心态，不让Muse因不满返工 |

作者输出不合格时，保留审查意见并修订。默认可持续审查到通过；这不保证一定收敛，也不代表可以无限免费运行。

程序的结构校验检查字段、日期、身份、来源范围和锁定关系；Critic补充语义审查。**通过审查不等于故事绝对真实、完全一致或心理学上有效。** 荣格八维仅是创作参数，不是诊断或测评结论。

### 共同经历为什么要逐人拆分

同一事件可以被两人记得，但理解不同。Aphrodite提供逐人观察，Mnemosyne只继承本人有权知道的材料。不能把“你不知道对方的以下秘密”直接写给学生，因为看到秘密就已污染上下文。

Icelos沿用该边界；Muse接收获准披露内容，不接收另一份附有隐瞒秘密的全知说明。披露权限标签和来源引用有助于检查，但不能完全排除模型语义幻觉。

## 5. 剧情日历与报名状态

| 剧情日期 | 事项 |
| --- | --- |
| 2025-04-23，周三 | 前期自然生活设定截止 |
| 2025-04-24，周四 | 公告发布、开放报名 |
| 2025-05-04，周日 | 报名截止 |
| 2025-05-05，周一 | 玩家决定并发布答辩入围名单 |
| 2025-05-10，周六 | 答辩并现场颁奖 |

Chronos只生成4月24日至5月4日，不代替玩家决定入围或获奖。两人可以晚填、不填、填写一部分、填完不交或提交后撤回。

填写与提交是不同状态：正文是否完成、首次填写和更新日期、提交日期应彼此一致。只有满足校验且当前已提交的报名快照可导出游戏报名包，不能拿未提交草稿冒充正式申请。基本资料从设定映射，缺失信息标待补充，不让模型猜学号或电话。

玩家入围结果是外部事件。操作者在此录入决定，不代表模型自己作出决定，也不等于工具已接入游戏端决策界面。

## 6. 运行控制、超时与重试

- **进行一步**：执行一个作者或审查任务；分片也可能单独算一步。
- **完成当前阶段**：持续运行本阶段作者与审查者，通过后暂停。
- **全自动至结束**：持续推进，但会在玩家入围等外部门槛停下。
- **暂停**：停止后续调度；不同引擎对在途请求的处理有差异，不要依赖暂停来节省已经发出的上游费用。
- **停止**：终止当前调度并阻止停止后的结果继续提交。保存需要的工程后再新建任务。

前期网页请求的上游等待默认300秒，网页总等待比设定多30秒；可在设置中调整。上游服务商自己的超时不会因本地等待放长而消失。

自动重试可勾选，默认关闭，默认额外重试2次。覆盖临时网络／超时错误及输出JSON、字段、结构校验错误；结构失败会反馈差异，不降低校验标准。认证或地址等不可恢复错误不应反复请求。

**超时断开不保证上游模型已经停止。重试可能重复计费；“无限修订”与“失败自动重试”也是两种不同机制。** 演示时优先示例，小人数真实测试时注意调用次数。

## 7. 四类文件不要混用

| 文件 | 用途 | 是否适合继续创作 |
| --- | --- | --- |
| 统一工程 `model-couple-unified-project-v1` | 保存前后阶段状态与关联，可导入恢复 | 是，推荐定期保存 |
| 运行设定 `model-couple-runtime-v1` | 已审定学生、关系和个人接管包 | 不是完整创作工程 |
| 游戏报名包 `model-couple-game-package-v1` | 已提交报名表及角色资料，供游戏消费端使用 | 不是编辑工程 |
| 答辩准备包 `model-couple-preparation-package-v1` | 共同剧本、个人态度及答辩所需记忆 | 不是现场答辩记录 |

统一工程支持旧creation工程、旧作者工程及运行设定的兼容入口；不完整或身份关联不一致的文件会拒绝。导入恢复保持暂停，不应自动产生付费调用。

游戏包中`player_visible`与`role_private`是逻辑分区，不是加密。拿到整个文件的人能读取私人资料；游戏消费端必须实施按人隔离，不能把整个包塞进每个学生的提示词。

## 8. 文件位置

```text
tools/
  common/config.json              # 唯一共享API配置，含明文密钥
  creation/
    student_server.py             # 本地服务入口
    student-foundry.html          # 统一工作台
    unified.js                    # 阶段装配、交接与统一工程
    author-panel.html             # 后续作者控件模板
    author.py                     # Chronos / Icelos / Muse作者引擎
    runtime.py                    # 设定校验、既有协议与旧流程兼容
    logs/                         # 前期调用日志及工程产物
    data/author_projects/          # 后续作者工程持久化
    data/sessions/                 # 旧会话兼容数据
    legacy/                       # 旧聊天页面，不是当前主线
    README.md
    演示文稿/
```

旧`/simulation/`链接跳转到统一creation。遗留simulation目录可能保留旧数据与跳转壳，不要把它当垃圾目录直接清除。

## 9. 常见问题

**页面空白、作者控件加载失败**：确认通过HTTP入口访问，重启新版Python服务并刷新。双击HTML不能加载完整统一工作台。

**导入后不能运行Chronos**：检查是否已完成严格审核、是否开启“对接颁奖”、是否已选有效情侣。旧设定缺对接标志时需要显式启用，不自动替你授权后续调用。

**显示没有情侣**：先检查文件类型。工程通常把数据放在内部状态，不能手工把它当成任意运行JSON；使用工作台对应导入入口，保留完整原件。

**一直等在5月5日**：这是有意的外部门槛，需要录入玩家入围决定。模型无权越过。

**请求超时**：区分前端总超时、本地后端等待和上游HTTP错误；检查耗时、模型输出量、服务商状态，再调整等待与重试。不要原样无限点击。

**输出结构错误**：保存具体字段路径与日志。可选有限重试；不要手动把审核状态改成通过来绕过。

**刷新后进度不见**：前期页面状态不能仅靠刷新恢复。导入导出的统一工程；后续作者工程可按工程ID暂停恢复。不要用运行设定替代工程备份。

**旧配置修改没效果**：以`tools/common/config.json`为准，并确认后端已重启采用新路径。不要在求助截图中露出密钥。

## 10. 当前边界与演示话术

- 前四与后四阶段共用外壳、各自渲染轨迹，尚非八阶段混排的单一时间线。
- 后续一次交接处理选定的一对情侣，不是自动批量处理所有情侣。
- 本地测试覆盖流程、协议、日期、隔离和恢复；示例通过不代表每种真实接口和长文本都能通过。
- 现有工具未在此链路自动完成`branches/latest`游戏端接入，也未实现现场自由答辩。
- 不对外发布、真实报名或自动向学校提交材料；这里的“提交”是游戏内状态。

推荐介绍：**“它不是让几个模型自由群聊，而是将事实创作、个人记忆、披露选择与舞台包装分成明确的产物和审核节点。玩家决定制度结果，工具不替玩家选入围与获奖。”**

## 11. 开发者验证（可选）

以下测试不调用真实模型；务必在项目环境运行，日志恢复类测试可能重建既有测试恢复产物。

```bash
node tools/creation/test_unified.cjs
node tools/creation/test_student_foundry.cjs
node tools/creation/test_creation_retry.cjs
node tools/creation/test_author_page.cjs
python -m unittest discover -s tools/creation -p "test_*.py"
```

演示PPT位于：`演示文稿/Creation工具使用与原理/Creation工具使用与原理.pptx`。
