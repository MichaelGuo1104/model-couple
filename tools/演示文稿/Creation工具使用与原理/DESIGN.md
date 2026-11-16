# Creation 工具使用与原理：演示设计

## 需求与证据
- 受众：首次接触工具的同事；目标：理解用途、运行顺序与边界，能安全进行第一次演示。
- 中文，12页，约10分钟。仅制作PPT；无外部图片，无模型调用，不修改代码或README。
- 依据：student-foundry.html、unified.js、author.py、student_server.py、author-panel.html及对应tests。未读取配置值；测试仅阅读，未执行。
- 故事时间固定2025年，不等于演示日期。游戏latest连接状态仅能描述为所读creation链路未见自动接入，不对游戏端整体下结论。

## 全局视觉约定
- 1280×720，安全区四边60px；原生可编辑文本与Box流程节点。无图片资产；assets保留，后续资源名必须ASCII。
- 配色：主色#191E26，辅色#303947，强调#86C8BD，底色#101318，正文#E8EAF0，次要文字#A1ACBC。无阴影。圆角8px。
- 字体：Microsoft YaHei；西文沿用同族。封面72px，页面标题36px，节点小标题24px，正文20px，脚注14px；Hero主句56px。每页最多4种文字样式。
- 母题：内容页标题下贯通细线；页尾固定y670。封面、结束页无页尾。
- 结构图全部使用原生形状与文本，不使用位图流程图；少字优先，以讲者提示补充。内容少的页面显式采用留白型构图。
- 节奏：P1/P7/P10为Hero；其余为信息页，P12兼结束。相邻页改变构图轴与锚点，避免等宽卡片连排。

## 逐页设计
### 01 Creation 众神创作工作台
- type: cover；role: hero；rhythm: peak
- layout: 左对齐大字报；visual: L1原生大字，右下关系链；visual_role: anchor
- density: 约45字 / 图片0张 / 留白45%
- anti_pattern: 不铺满角色名单，不加页尾
- description: 点明从人物到准备包的离线作者工作台，不包装为学生自由聊天。

### 02 先造故事，再交付可接管材料
- type: content；role: supporting；rhythm: valley
- layout: 左侧产物主链，右侧用途窄栏；visual: L1原生产物流；visual_role: evidence
- density: 约100字 / 图片0张 / 留白30%
- anti_pattern: 不把工程与游戏包混为一谈
- description: 人物、关系、私有接管包；可续写工程、运行设定及颁奖分支材料。

### 03 一个开关，两条终点不同的路线
- type: content；role: supporting；rhythm: valley
- layout: 上方共享主干，下方分叉，非对称；visual: L1分叉流程；visual_role: evidence
- density: 约110字 / 图片0张 / 留白30%
- anti_pattern: 不说开启后自动为全部情侣付费
- description: 纯恋爱四阶段结束；对接颁奖选择一对交接，等待外部入围，再准备。

### 04 八阶段：作者创作，C_xxx独立审查
- type: content；role: supporting；rhythm: valley
- layout: 两条纵向阶段链，上下游关联；visual: L1八阶段原生节点；visual_role: evidence
- density: 约180字 / 图片0张 / 留白25%
- anti_pattern: 不把八阶段误写为八次API调用
- description: 前四主体与后四主体，对应C_审查；局部修订与锁定，审核非真实性保证。

### 05 从本地服务进入，不从HTML双击开始
- type: content；role: supporting；rhythm: valley
- layout: 左命令与入口，右配置与风险；visual: L1原生启动路径；visual_role: evidence
- density: 约150字 / 图片0张 / 留白28%
- anti_pattern: 不出现真实密钥，不混淆两引擎超时设置
- description: 根目录python tools/creation/student_server.py，127.0.0.1:8765/creation/，共享配置路径，密钥明文风险；前四300+30，作者后端300。

### 06 前三步：造人、牵线、写生活
- type: content；role: supporting；rhythm: valley
- layout: 三级错落递进；visual: L1原生阶梯链；visual_role: evidence
- density: 约120字 / 图片0张 / 留白30%
- anti_pattern: 不把Aphrodite说成可重写锁定框架
- description: 人物独立生活；完整关系年表；事件、习惯、逐人观察。历史截止2025-04-23，不预埋颁奖。

### 07 有来源，不等于全知
- type: content；role: hero；rhythm: peak
- layout: 左大字主张，右分区权限流，留白型；visual: L1原生知识边界图；visual_role: anchor
- density: 约100字 / 图片0张 / 留白42%
- anti_pattern: 不暗示source_refs保证语义真实，不暗示分区即加密
- description: Mnemosyne逐人编译，仅白名单来源；本人观察/解释/私有信息分开；对方秘密和全知叙事不自动进入。

### 08 Chronos推进生活，也记录报名是否发生
- type: content；role: supporting；rhythm: valley
- layout: 横向日期轴与下方状态轨；visual: L1时间轴；visual_role: evidence
- density: 约130字 / 图片0张 / 留白30%
- anti_pattern: 不将愿意报名等同submitted
- description: 2025-04-24至05-04；个人not_filled/partial/complete，报名not_submitted/submitted/withdrawn；提交须双同意、双正文及合法日期。

### 09 入围由玩家决定，准备链只向前
- type: content；role: supporting；rhythm: valley
- layout: 顶部门槛与横向单向链；visual: L1门槛和授权流程；visual_role: evidence
- density: 约140字 / 图片0张 / 留白27%
- anti_pattern: 不画Icelos回跳Muse的反馈箭头
- description: 5/5显式录入外部入围事件；Icelos三层授权，Muse写准备剧本，Icelos逐人态度不改稿。

### 10 演示先跑通，再花钱
- type: content；role: hero；rhythm: peak
- layout: 左大字示例，右纵向操作序列，留白型；visual: L1大字与执行顺序；visual_role: anchor
- density: 约135字 / 图片0张 / 留白40%
- anti_pattern: 不暗示固定示例是真实AI或实测质量
- description: 先2人1对示例，观察审查/锁定与入围暂停；再真实API一步；导出统一工程并暂停恢复。默认关闭失败重试；重试可能重复计费，无限修订也收费。

### 11 四种导出，解决四件不同的事
- type: content；role: supporting；rhythm: valley
- layout: 非等宽双列查读表，外层边框；visual: L1原生对照结构；visual_role: evidence
- density: 约170字 / 图片0张 / 留白25%
- anti_pattern: 不推荐将完整工程交给玩家；不说运行设定可无损续写
- description: 工程保进度；运行设定为审定背景；game为已提交报名快照且含私有分区；准备包为全部准备审定后的共同剧本与逐人心态，不含审查/后台意图。

### 12 当前边界：先把准备交接做好
- type: ending；role: supporting；rhythm: valley
- layout: 左侧当前能力，右侧未实现与接入；visual: L1原生边界清单；visual_role: evidence
- density: 约145字 / 图片0张 / 留白32%
- anti_pattern: 不把未来现场答辩列为已实现，不给游戏latest整端作无证据断言
- description: 一次交接一对，未见creation自动接入游戏latest；未来5/10现场只有学生、无Critic尚未实现；隔离由消费端落实；模型审查不是真实性保证。无页尾。
