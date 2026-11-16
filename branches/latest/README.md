# 优秀情侣奖（latest）

当前游戏仅保留优秀情侣奖，少年奖路线及其专用材料、答辩、裁定与颁奖页面已删除。流程为：**筹备会议 → 核阅并发布通知 → 双人报名审阅 → 玩家决定入围 → 双人答辩 → 结束**。不评分、不决定获奖、不颁奖、不发布获奖结果，也没有自由答辩 AI 接口。

## 1. 本地开发预览：无需构建

前端为 Vue 3 + Vite。以下命令从项目根目录 `D:/gamestuff/model-couple` 执行：

```bash
npm --prefix branches/latest run dev -- --port 5173 --strictPort
```

浏览器打开 **http://127.0.0.1:5173/**。`package.json` 的 dev 脚本固定监听 `127.0.0.1`；显式端口与 `--strictPort` 避免占用时悄悄换端口。若5173已被占用，先确认现有进程，不擅自结束；需要另开时显式换端口并按终端地址访问。

在 `branches/latest` 目录内等价命令是 `npm run dev -- --port 5173 --strictPort`。依赖已安装时直接启动；缺依赖时可先 `npm --prefix branches/latest ci`。当前包使用 Vite 7.3.6，Node.js 需满足其版本要求（20.19+ 或22.12+等受支持版本）。

**预览主线无需 Python 后端、无需构建或 `npm run preview`，不要双击根 `index.html`，也不要将旧 `dist` 当最新代码。** 本次仅更新文档，不构建、打包或发布。

## 2. 可选论坛后端：与游戏预览分开

前端主线、报名和答辩使用本地静态数据；后端缺失时论坛会提示不可用，不阻塞主线。Vite 配置没有 `/api` 代理；前端调用相对路径 `/api/...`，不能认为启动5173和8780两个服务就会自动联通，也不要绕过后端同源限制。

从项目根目录可启动**无真实模型调用的 MOCK 后端**：

```bash
python branches/latest/server.py --mock --port 8780
```

后端默认仅监听 `127.0.0.1:8780`，健康检查为 **http://127.0.0.1:8780/api/health**，SQLite 默认保存于 `branches/latest/runtime/campus.sqlite3`；可用实际存在的 `--db` 参数指定独立测试数据库。MOCK 是测试桩，不是真实 AI。该服务默认静态目录为 `branches/latest/dist`，不会编译 Vue 源码；已有 dist 可能过时。因此此命令是可选后端入口，**不是无构建的最新游戏预览命令**。

真实论坛后端用 `python branches/latest/server.py --port 8780 --config branches/latest/config.json`，或通过 `ANY_AWARD_AI_CONFIG` 指定配置路径。后端不会因同目录存在 config.json 自动加载；显式选择真实配置后，开局日常帖、通知讨论、发帖／回帖等前端操作可能产生费用，不能当无费用验收。配置格式参考 `config.example.json`，不公开密钥、不读取或修改 tools 的共享配置。本次不启动真实后端、不调用真实模型，也不为接入论坛修改代理或构建静态目录。

保留共享论坛、人物图片、统一网关、SQLite 与同源／静态白名单安全边界。校史种子为空，未删除项目外原始卷宗。废弃自由答辩接口返回404，结果发布返回409；不要沿用旧版答辩或结果生成说明。

## 3. 内容来源、白名单提取与人工修订

当前唯一完整报名为 `tools/common/successful-run.json` 中 c1：苏晚棠 & 郑亦航。游戏不导入整个工程，不沿用源档 nomination，而由玩家重新决定入围并可撤销。

若以后明确需要更新静态公开数据，从项目根目录执行：

```bash
node branches/latest/scripts/extract-couple.mjs tools/common/successful-run.json
```

若在 `branches/latest` 内执行，源路径必须改为：

```bash
node scripts/extract-couple.mjs ../../tools/common/successful-run.json
```

**参数已核对：脚本只读取第一个位置参数 `process.argv[2]` 作为源文件，不接受输出参数；输出固定覆盖 `branches/latest/src/coupleCandidates.js`。** 本次不执行提取、不改源包或生成代码。提取前应先按作者 v2 校验源工程；提取器本身只作 c1、双方授权、两页及非空正文／发言等有限检查，不等同完整作者审查。

提取范围：

- `author.game_snapshot.player_visible.application` 的两页公开报名字段、第一人称正文、参与确认、公开授权、提交状态、通知及剧情提交日期。
- `author.results.script.scenes` 按顺序取 dialogue/chorus 的发言，人物 ID 映射为姓名；略过 action 段及动作、情绪、时长等。发言条数随源剧本变化，不固定22条。
- 有人工修订时附公开声明。不包含 role_private、记忆、认知、秘密、backstage、来源引用、审查记录、candidate_token 或源 nomination，也不将整份 successful-run 发往浏览器。

报名正文面向评委，以个人第一人称说明学业、专业实践、成长、互助及参评理由；授权隐私提交说明独立显示，不塞进正文。基本字段保留原年级、专业和“待补充”，不虚构学校或联系方式。报名授权由操作者声明，**不是学生签署**；公开授权仍为“未授权”。这里是本地游戏展示，不代表获准对外发布。

排名由工具 `runtime.py → extracted_rank` 从已有 `grade_rank` 或成绩源文明确排名提取；绩点不替代排名，没有明确排名则待补充。苏晚棠为**本科专业前5%**，不是研究生排名；郑亦航为**本科年级排名中游**，不以3.2绩点推算排名。保留学段差异，不补造研究生排名。

当前源档明确记录 `author.manual_revision.actor=operator`、`model_reviewed=false`、日期、原因及修订摘要；`manual_revision.original_author` 保留原 author 与历史审查，原始人物保留。人工修订不伪造新的 C_Muse/C_Chronos 批准，不称为模型重新生成或模型复审通过。UI 同样显示“未经模型复审、非重新签署”声明；结构校验通过不等于内容经模型审查。

## 4. 作者工具与游戏的分工

作者工具见 `../../tools/creation/README.md`。当前 author v2 为九阶段：Prometheus 人物 → Cupid 框架 → Aphrodite 细节 → Mnemosyne 记忆 → Chronos 报名剧情 → **独立 Muse 正式表** → Icelos 披露 → **不同提示词的 Muse 答辩** → Icelos 读稿态度。

Chronos 只写剧情且最终双方必定同意报名，不写正式表；表锁定后才有报名快照，披露准备由玩家外部入围门控。正式表须有履历依据；答辩允许基于公开履历和已披露素材的宣传／舞台加工，人物自然接话而不念内部 ID 或流程政策，但不把加工写回真实履历、记忆、经历或报名快照。Critic 检查秘密与素材边界；剧本 Critic 不审真实性、不对情侣评分、不设权重，不替玩家判断。旧 author v1 不静默迁移，须保留原档并新建 v2。

游戏只是消费提取的公开报名与文本发言，不运行上述模型流水线，不产生答辩 AI 请求。答辩到 `coupleEnd` 即结束，无获奖／颁奖分支。存档键为 `excellent-couple-v2`，不读取废弃路线存档，也不删除浏览器旧数据；报名选择、答辩进度和结束状态可刷新恢复。

## 5. 实际存在的验证命令

从项目根目录执行，均不构建、不调用真实模型：

```bash
node branches/latest/scripts/test-awards.mjs
node branches/latest/scripts/test-chat-clock.mjs
```

后端测试需在 `branches/latest` 目录内执行，以匹配模块导入：

```bash
python -m unittest discover -s tests -v
```

单奖项测试设计上只读 successful-run 和公开提取结果，检查排名、人工修订审计、敏感键排除、动态答辩条数、玩家入围与进度恢复。**本次实跑 `test-awards.mjs` 因脚本仍硬编码旧 `tools/successful-run.json` 而报 ENOENT；实际文件已在 `tools/common/successful-run.json`，不能称该测试通过。** 本次只改文档，不修改脚本、不复制源档填补旧路径。上面的提取命令已使用实际新位置，提取器接收位置参数，不受该测试硬编码限制。后端测试使用 MOCK、临时 SQLite 和本地测试服务，不读真实密钥。

浏览器测试脚本也实际存在：

```bash
node branches/latest/scripts/test-awards-browser.cjs
```

先准备好本地 Vite 开发服务，默认访问5173；可用 `AWARD_TEST_ENTRY` 指向另一个已运行的本地开发地址。脚本固定使用 `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` 和调试端口9367，自动新建系统临时档案、阻断全部 `/api/*`，验证主线至答辩结束及刷新恢复，最后关闭自己启动的浏览器。无需预先另开测试浏览器，务必确认9367未被其他进程使用；不应指向真实玩家页面或真实论坛数据库。该脚本不是手工截图视觉验收。

旧的 `test-result-publication.mjs`、少年奖答辩测试等已不在当前 scripts 中，不再作为 latest 测试命令。工具侧测试见 Creation README；本次实际执行结果以工作日志和完成报告为准，不将历史通过记录冒充本次运行。
