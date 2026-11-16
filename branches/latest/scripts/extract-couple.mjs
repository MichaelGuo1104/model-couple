import fs from 'node:fs';

// 源包仅在本地提取时读取；前端只接收明确列出的公开字段。
const source = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const author = source.author;
const snapshot = author.game_snapshot;
const application = snapshot.player_visible.application;
if (snapshot.source.couple_id !== 'c1' || !snapshot.submission.both_authorized || application.pages.length !== 2) throw new Error('报名快照不完整');
const fields = ['姓名', '性别', '专业', '年级', '班级', '学号', '电子邮箱', '联系电话', '绩点', '绩点排名'];
const pages = application.pages.map(page => ({
  studentId: page.student_id,
  fields: Object.fromEntries(fields.map(key => [key, page.fields[key] ?? '待补充'])),
  statement: page['个人陈述（300字左右）'],
  participation: page['参与确认'],
  publicity: page['公开授权'],
  status: page['提交状态'],
}));
const names = Object.fromEntries(pages.map(page => [page.studentId, page.fields['姓名']]));
const speech = author.results.script.scenes.flatMap(scene => scene.beats)
  .filter(beat => ['dialogue', 'chorus'].includes(beat.kind))
  .map(beat => ({ kind: beat.kind, speaker: beat.performers.map(id => names[id] || id).join(' & '), text: beat.text.replace(/\bs[34]\b/g, id => names[id]) }));
if (!speech.length || pages.some(page => !page.statement)) throw new Error('报名正文或答辩发言为空');
const data = [{ id: 'c1', name: pages.map(page => page.fields['姓名']).join(' & '), submittedAt: snapshot.submission.submitted_at_story, notice: application.notice, revision: author.manual_revision ? '操作者于'+author.manual_revision.date+'依据原始人物资料手工修订报名与答辩，未重新调用模型、未经模型复审；不表示学生重新签署。' : '', pages, speech }];
fs.writeFileSync(new URL('../src/coupleCandidates.js', import.meta.url), `// 仅含报名公开字段与精简发言，不包含人物私有包。\nexport const coupleCandidates = ${JSON.stringify(data, null, 2)};\n`);
