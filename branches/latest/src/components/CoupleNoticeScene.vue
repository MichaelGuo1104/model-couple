<script setup>
import { computed, ref, watch } from 'vue';
import { people, image } from '../content.js';

const props = defineProps({ school: String, player: String, published: Boolean, campusMessage: String });
defineEmits(['publish', 'forum', 'history', 'title', 'continue']);
const enlarged = ref(false);
const showingForm = ref(false);
const documentView = ref(null);
const schoolName = computed(() => props.school || '学校');
const students = ['甲', '乙'];
const fieldRows = [['姓名', '性别', '专业'], ['班级', '学号'], ['电子邮箱', '联系电话'], ['绩点', '绩点排名']];
const instructions = [
  '一、双方分别知情、自愿确认；参与评选与公开展示分别授权。',
  '二、仅填写自愿提供且与评选有关的资料，不提供私人聊天、社交账号或密码。',
  '三、未提供的信息保留待补充；不得代签或假造授权。',
  '四、2025年4月24日周四开放报名，5月4日周日截止。收到空白表不代表报名。',
];
const noticeParagraphs = [
  ['一、参与原则。', '学生甲、学生乙须分别知情、自愿同意参与；任何一方均可选择不参加或撤回，不因是否恋爱、是否申报或是否获奖受到评价。'],
  ['二、材料边界。', '分别陈述个人学业、专业实践、成长、关系支持与参评理由，不设性别、交往时长、消费金额或社交热度门槛，不以这些因素排名。不收集私人聊天记录、社交账号、密码或其他与评选无关的隐私。'],
  ['三、公开授权。', '参与评选与对外公开分别征求双方意见；公开展示须另行取得双方自愿授权，不同意公开不影响参与。'],
  ['四、工作安排。', '2025年4月24日周四开放报名，5月4日周日截止，5月5日周一由玩家决定入围，5月10日周六答辩。入围不等于获奖；本游戏阶段仅实施至答辩结束，不进入颁奖。'],
];
function switchDocument(form) {
  showingForm.value = form && props.published;
  if (documentView.value) {
    documentView.value.scrollTop = 0;
    documentView.value.scrollLeft = 0;
  }
}
watch(() => props.published, value => { if (!value) switchDocument(false); });
</script>

<template>
  <section class="couple-notice-scene" aria-label="优秀情侣奖通知与空白表样">
    <div ref="documentView" class="notice-view" :class="{ enlarged }" tabindex="0" :aria-label="showingForm ? '双面打印报名表：封面、申请人甲、申请人乙、第4页起佐证材料，可滚动核阅' : '正式通知，可滚动核阅'">
      <article v-if="!showingForm" class="a4-page official-notice" aria-label="优秀情侣奖评选通知" :data-published="published">
        <div class="notice-letterhead" :style="{ fontSize: (schoolName.length > 12 ? 24 : schoolName.length > 7 ? 30 : 38) + 'px' }">{{ schoolName }}文件</div>
        <div class="notice-number">校学〔2025〕2号</div>
        <div class="notice-redline"></div>
        <h1>关于开展2025年度<br>“优秀情侣奖”评选工作的通知</h1>
        <div class="notice-body">
          <p class="notice-recipient">各学院：</p>
          <p>为尊重学生自主选择，倡导平等、尊重与共同成长，现发布2025年度“优秀情侣奖”评选通知及空白报名表样。有关事项通知如下。</p>
          <p v-for="[heading, text] in noticeParagraphs" :key="heading"><b>{{ heading }}</b>{{ text }}</p>
          <div class="notice-signature"><span>{{ schoolName }}</span><span>2025年4月24日</span></div>
        </div>
        <div class="notice-imprint"><span>{{ schoolName }}办公室</span><span>2025年4月24日印发</span></div>
        <div class="page-number">— 1 —</div>
      </article>

      <template v-else>
        <article class="a4-page form-page cover-page" aria-label="报名表第1页：封面与填表说明">
          <div class="form-kicker">{{ schoolName }} · 2025年度 / 空白表样</div>
          <div class="cover-title"><p>2025年度</p><h1>优秀情侣奖<br>申 报 表</h1><span>双人申报 · 双面打印</span></div>
          <table class="application-table cover-table" aria-label="封面信息留白"><tbody>
            <tr><th>申请人甲姓名</th><td></td></tr>
            <tr><th>申请人乙姓名</th><td></td></tr>
            <tr><th>填表日期</th><td>　　　年　　月　　日</td></tr>
          </tbody></table>
          <section class="instructions"><h2>填表说明</h2><p v-for="line in instructions" :key="line">{{ line }}</p></section>
          <p class="booklet-note">装订顺序：封面 → 申请人甲资料 → 申请人乙资料 → 佐证材料。<br>双面打印，长边翻页；第1／2页为第一张纸正反面，第3／4页为第二张纸正反面，后续材料依次接续。</p>
          <div class="form-footer">空白表样预览 · 不代表已填写、签署或提交</div>
          <div class="page-number">— 1 —</div>
        </article>

        <article v-for="(student,index) in students" :key="student" class="a4-page form-page applicant-page" :aria-label="'报名表第'+(index+2)+'页：申请人'+student+'资料'">
          <div class="form-kicker">优秀情侣奖申报表 · 申请人{{ student }}（学生{{ student }}）资料</div>
          <h1>申请人{{ student }}资料</h1>
          <table class="application-table applicant-table" :aria-label="'申请人'+student+'资料表（空白）'">
            <colgroup><col v-for="i in 6" :key="i" /></colgroup>
            <tbody>
              <tr><th colspan="6" class="section-heading">一、基本信息</th></tr>
              <tr v-for="(row,rowIndex) in fieldRows" :key="rowIndex">
                <template v-for="field in row" :key="field">
                  <th><span class="required">*</span>申请人{{ student }}{{ field }}</th>
                  <td :colspan="row.length===3?1:2" :aria-label="'申请人'+student+field+'（空白）'"></td>
                </template>
              </tr>
              <tr><th colspan="6" class="section-heading">三、个人陈述</th></tr>
              <tr><th colspan="6" class="statement-label"><span class="required">*</span>申请人{{ student }}个人陈述 <span>（300字左右）</span></th></tr>
              <tr><td colspan="6" class="statement-cell" :aria-label="'申请人'+student+'个人陈述留白，300字左右'"></td></tr>
            </tbody>
          </table>
          <p class="required-note">注：带“*”项为必填项。本页为空白表样，未填写、未签署、未提交。</p>
          <div class="form-footer">{{ index===0?'第一张纸 · 反面':'第二张纸 · 正面' }} / 双面打印 · 长边翻页</div>
          <div class="page-number">— {{ index+2 }} —</div>
        </article>

        <article class="a4-page form-page evidence-page" aria-label="报名表第4页起：佐证材料">
          <div class="form-kicker">优秀情侣奖申报表 · 附件</div>
          <h1>佐证材料</h1>
          <p class="evidence-intro">第4页起依次附佐证材料。以下仅为空白编排示意，不代表已收到任何材料。</p>
          <table class="application-table evidence-table" aria-label="佐证材料目录（空白）"><thead>
            <tr><th>序号</th><th>材料名称</th><th>所属申请人</th><th>页码</th></tr>
          </thead><tbody><tr v-for="i in 4" :key="i"><td></td><td></td><td></td><td></td></tr></tbody></table>
          <div class="evidence-placeholder">佐证材料粘贴／复印区域<br><small>空白占位 · 不提供上传或收取功能</small></div>
          <p class="booklet-note">佐证材料接续页码，继续双面打印、长边翻页；本页为第二张纸反面。实际材料页数以正式填报时为准。</p>
          <div class="form-footer">空白表样预览 · 不代填或生成佐证材料</div>
          <div class="page-number">— 4 —</div>
        </article>
      </template>
    </div>

    <aside class="notice-sidebar">
      <div class="eyebrow">{{ showingForm ? '空白表样　／　仅供预览' : published ? '通知发布　／　公开核阅' : '公文拟稿　／　待核阅' }}</div>
      <img :src="image(people.zhou.thumb)" alt="周处长" draggable="false">
      <h2>周处长</h2>
      <p v-if="!published">{{ player || '主任' }}，通知已按会议原则拟好。双方分别自愿，实践为据，隐私从简，宣传另行授权。请您核阅后发布。</p>
      <p v-else-if="!showingForm">通知已发布。可核阅空白表样，或收取截至5月4日的完整报名。入围名单完全由您决定，委员会不参与干预。</p>
      <p v-else>这是双面打印的成册表样：第1页封面，第2页申请人甲资料，第3页申请人乙资料，第4页起附佐证材料。表样不代表已填写、签署或提交；已提交材料请通过收表入口核阅。</p>
      <div class="notice-status" role="status">{{ published ? '已发布 · 校学〔2025〕2号' : '拟稿 · 待核阅发布' }}</div>
      <button class="small" data-action="notice-zoom" :aria-pressed="enlarged" @click="enlarged = !enlarged">{{ enlarged ? '恢复页面大小' : '放大核阅' }}</button>
      <button v-if="!published" class="primary" data-action="publish-notice" @click="$emit('publish')">确认并发布通知</button>
      <button v-else-if="!showingForm" class="primary" data-action="preview-couple-form" @click="switchDocument(true)">预览空白报名表 →</button>
      <button v-else class="primary" data-action="back-couple-notice" @click="switchDocument(false)">← 返回正式通知</button>
      <button v-if="published" class="primary" data-action="collect-forms" @click="$emit('continue')">收取报名材料 →</button>
      <div v-if="published" class="notice-campus">
        <button class="small" data-action="open-forum" @click="$emit('forum')">校园论坛</button>
        <button class="small" data-action="open-history" @click="$emit('history')">查看校史</button>
      </div>
      <small v-if="published && campusMessage" class="feedback-status" role="status">{{ campusMessage }}</small>
      <button class="small title-button" data-action="back-title" @click="$emit('title')">返回标题</button>
      <small>游戏内剧情发布，不发送至外部平台。<br>A4比例页面，可滚动或触屏滑动核阅；放大后可横向滚动。日期与文号沿用剧本设定。<br>仅收取已有游戏内报名，不上传材料至真实学校。</small>
    </aside>
  </section>
</template>

<style scoped>
.couple-notice-scene{position:absolute;inset:0;display:flex;gap:70px;padding:40px 130px;background:#e5e1da}
.notice-view{width:920px;height:1000px;overflow:auto;padding:25px 115px;scrollbar-width:thin;flex:none;overscroll-behavior:contain}
.notice-view:focus-visible{outline:2px solid var(--red);outline-offset:3px}
.a4-page{width:630px;min-height:891px;background:#fff;color:#000;position:relative;box-sizing:border-box;box-shadow:4px 8px 18px #14141433;flex:none;margin-bottom:28px}
.notice-view.enlarged{padding:25px 12px}.notice-view.enlarged .a4-page{zoom:1.4}
.official-notice{padding:60px 60px 108px 62px;font-family:FangSong,'仿宋',SimSun,'宋体',serif}
.notice-letterhead{font-family:'方正小标宋简体','FZXiaoBiaoSong-B05S',SimSun,'宋体',serif;color:#d0241c;text-align:center;font-weight:700;white-space:nowrap;line-height:1.2;letter-spacing:3px}
.notice-number{font-size:16.933333px;line-height:29.633333px;text-align:center;margin-top:25px}
.notice-redline{height:1.05px;background:#d0241c;margin:3px 0 25px}
.official-notice h1{font-family:'方正小标宋简体','FZXiaoBiaoSong-B05S',SimSun,'宋体',serif;font-size:23.283333px;line-height:30px;font-weight:400;text-align:center;margin:0 0 20px}
.notice-body{font-size:16.933333px;line-height:29px;text-align:justify}
.notice-body p{margin:0;text-indent:2em}.notice-body .notice-recipient{text-indent:0}.notice-body b{font-family:SimHei,'黑体',sans-serif;font-weight:400}
.notice-signature{display:flex;flex-direction:column;align-items:flex-end;margin-top:16px;padding-right:2em;line-height:29px}.notice-signature span:first-child{max-width:100%;overflow-wrap:anywhere}
.notice-imprint{position:absolute;left:72px;right:66px;bottom:57px;border-top:1px solid;border-bottom:1px solid;padding:6px 1em;display:flex;justify-content:space-between;gap:10px;font-size:14px}
.notice-imprint span:first-child{overflow-wrap:anywhere}.notice-imprint span:last-child{white-space:nowrap}
.page-number{position:absolute;right:66px;bottom:25px;font:14px SimSun,'宋体',serif}
.form-page{padding:42px 46px 75px;font-family:FangSong,'仿宋',SimSun,'宋体',serif;font-size:15px;line-height:1.65}
.form-kicker{font:13px SourceHanSans,sans-serif;color:#666;letter-spacing:2px}
.form-page h1{text-align:center;font:24px/1.5 SimSun,'宋体',serif;margin:14px 0}
.preview-warning{border:1px solid #9c322b;padding:8px 10px;color:#8a241c;margin:0 0 10px;font-size:15px}
.form-note{font-size:14px;margin:0 0 12px}.form-page h2{font:700 16px/1.6 SimSun,'宋体',serif;margin:10px 0 6px}.form-page h3{font:700 15px/1.6 SimSun,'宋体',serif;margin:10px 0 4px}
.student-info{border:1px solid #777;margin-bottom:10px;padding:0 10px 10px}.student-info h2{margin-top:6px}
.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px 20px}.info-grid>div{display:flex;gap:12px;align-items:baseline}.blank-line{flex:1;border-bottom:1px solid #999;min-height:18px}
.form-section p{margin:0;font-size:14px}.writing-lines{background:repeating-linear-gradient(to bottom,transparent 0,transparent 25px,#aaa 25px,#aaa 26px);margin:3px 0 10px}.one-line{height:26px}.practice-lines{height:78px}.boundary-lines{height:52px}
.privacy-note{font-size:14px;margin:12px 0 0;padding-top:8px;border-top:1px solid #aaa}
.form-footer{font-size:12px;color:#666;margin-top:14px}.consent-block{border:1px solid #777;padding:6px 12px 12px;margin:14px 0}.consent-block p{font-size:14px;margin:4px 0 8px}.consent-block .blank-options{font-size:16px;margin:12px 0}
.signature-row{display:flex;gap:20px;font-size:14px;margin-top:12px}.signature-row>span{display:flex;flex:1;white-space:nowrap}.signature-row i{border-bottom:1px solid #999;flex:1;min-width:45px}
.publicity-options{border-top:1px solid #aaa;border-left:1px solid #aaa}.publicity-options>div{display:flex;border-bottom:1px solid #aaa;border-right:1px solid #aaa;padding:4px 8px;gap:30px}.publicity-options>div>span:first-child{width:50px}
.notice-sidebar{width:520px;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:14px}.notice-sidebar img{width:110px;height:110px;border:1px solid var(--ink)}.notice-sidebar h2{font-size:32px;font-weight:400;margin:0}.notice-sidebar p{font-size:25px;line-height:1.8;margin:0}.notice-sidebar small{font-size:16px;line-height:1.8}.notice-sidebar .eyebrow{font-size:18px}
.notice-status{font-size:20px;color:var(--red);border-bottom:1px solid;padding-bottom:10px}.notice-campus{display:flex;gap:16px}.feedback-status{max-height:90px;overflow:auto;color:var(--red)}.title-button{align-self:flex-start}
.form-page:not(.consent-page){font-size:13px;line-height:1.4;padding-top:28px;padding-bottom:60px}.form-page:not(.consent-page) .form-note,.form-page:not(.consent-page) .privacy-note,.form-page:not(.consent-page) .form-section p{font-size:12px;line-height:1.4}.form-page:not(.consent-page) h2{font-size:15px;margin:6px 0 3px}.form-page:not(.consent-page) h1{margin:8px 0}.form-page:not(.consent-page) .preview-warning{font-size:13px;padding:6px 8px}.form-page:not(.consent-page) .student-info{margin-bottom:7px;padding-bottom:7px}.form-page:not(.consent-page) .info-grid{gap:5px 20px}.form-page:not(.consent-page) .practice-lines{height:52px}.form-page:not(.consent-page) .boundary-lines{height:26px}
.form-page{height:891px;min-height:891px;padding:40px 46px 65px!important;font-size:14px!important;line-height:1.65!important}.form-page .form-footer{position:absolute;bottom:56px;left:46px;right:46px;margin:0;font-size:11px}.application-table{border-collapse:collapse;width:100%;table-layout:fixed;font:14px/1.6 SimSun,'宋体',serif;color:#111}.application-table th,.application-table td{border:1px solid #333;padding:7px 8px;vertical-align:middle;overflow-wrap:anywhere}.application-table th{font-weight:400;text-align:center;background:#f6f5f1}.application-table td{background:#fff}.cover-title{text-align:center;margin:48px 0 36px}.cover-title p{font-size:19px;letter-spacing:4px}.cover-title h1{font-size:34px!important;line-height:1.8!important;margin:18px 0!important;letter-spacing:5px}.cover-title span{font-size:13px;color:#666;letter-spacing:3px}.cover-table{width:85%;margin:0 auto 28px}.cover-table th{width:36%}.cover-table tr{height:37px}.instructions h2{text-align:center;font-size:17px!important;margin:15px 0 10px!important}.instructions p{font-size:14px;line-height:1.8;margin:7px 0;text-align:justify}.booklet-note{font-size:12px;line-height:1.7;color:#555;margin:18px 0}.applicant-page h1,.evidence-page h1{margin:20px 0!important}.applicant-table tr:not(:has(.statement-cell)){height:46px}.applicant-table th{font-size:12px;padding:7px 4px}.application-table .section-heading{text-align:left;font-size:16px;font-weight:bold;letter-spacing:1px;background:#eae8e2}.application-table .statement-label{text-align:left;font-size:14px;background:#fff}.statement-label span:not(.required){font-weight:400;color:#555}.application-table .statement-cell{height:265px;vertical-align:top;background:repeating-linear-gradient(to bottom,#fff 0,#fff 30px,#ddd 30px,#ddd 31px);background-origin:content-box;padding:12px}.required{color:#a02b24}.required-note{font-size:12px;line-height:1.7;margin-top:14px}.evidence-intro{font-size:14px;line-height:1.8}.evidence-table th:first-child{width:12%}.evidence-table th:nth-child(2){width:43%}.evidence-table td{height:37px}.evidence-placeholder{height:310px;border:1px dashed #999;margin-top:24px;display:flex;flex-direction:column;justify-content:center;align-items:center;font-size:18px;color:#777;line-height:2}.evidence-placeholder small{font-size:12px}
</style>
