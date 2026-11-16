// All campus traffic is same-origin. Provider credentials never enter this module.
const messages={
 'AI is not configured; submit off-topic again after configuration':'尚未配置 AI。配置并重启后，可在论坛同步开局日常帖。',
 'AI is not configured; result announcement saved; submit the same result again after configuration':'结果公告已保存；尚未配置 AI。配置并重启后，请同步评选结果反馈。',
 'The first published result cannot be replaced':'本局已发布的结果公告不能覆盖；体验其他结果请重新开始。',
 'AI is not configured; announcement saved; submit notice again after configuration':'通知已保存；尚未配置 AI。配置并重启服务后，请在论坛同步公文反馈。',
 'AI is not configured; explicit retry required':'尚未配置 AI；你的内容已保存，配置后可明确重试。',
 'AI is not configured':'尚未配置 AI，请配置并重启本地服务。',
 'Only one player question; the original question cannot be changed':'每位学生只接受一个玩家问题；已提交的问题不可更换，失败时请重试原问题。',
 'Preparation must complete before asking':'请先等待答辩稿和钱教授问答生成完成。',
 'Defense attempt budget exhausted (60 per session)':'本局答辩 AI 请求已达60次上限（包含失败请求）。',
 'AI defense identity or output fields invalid':'答辩模型返回的身份或字段不正确，本次未保存生成内容，可明确重试。',
 'AI defense questioner must be qian':'答辩模型未按约定由钱教授提问，本次未保存生成内容。',
 'AI defense text invalid':'答辩模型返回的正文为空、过长或含非法字符，可明确重试。',
 'AI defense contains another candidate identity':'答辩模型混入了其他候选人的身份，本次内容已拒绝保存。',
 'Defense generation failed; explicit retry required':'答辩生成失败；不会自动重试，请确认后手动重试。',
 'Session AI budget exhausted':'本局 AI 请求预算已用完（20 次，包含失败请求）。',
 'Interrupted by server restart; explicit retry required':'上次生成被服务重启中断，确认后可重试。',
 'AI request failed or timed out':'模型请求失败或超时；不会自动重试，请检查配置与额度。',
 'AI output invalid or task failed':'模型输出不符合格式要求，未写入生成内容，可明确重试。',
 'Player nickname must not impersonate a forum persona':'请使用自己的昵称，不能冒用 AI 学生昵称。',
};
export function campusError(message){
 if(messages[message])return messages[message];
 if(message?.startsWith('AI JSON syntax invalid'))return '模型返回的 JSON 语法不完整或不合法：'+message;
 if(message==='AI schema invalid: thread count (expected 3, received 0)')return '模型返回了空帖子列表（要求3帖，实际0帖）。通知仍已发布，本次未写入帖子；请检查提示词后手动重试，不会自动重发。';
 if(message?.startsWith('AI schema invalid:'))return 'JSON 可解析，但内容结构不合要求：'+message.slice('AI schema invalid:'.length);
 if(message?.startsWith('AI upstream HTTP error'))return '模型服务返回 HTTP 错误（可能暂时不可用或额度限制）：'+message;
 if(message==='AI output truncated (finish_reason=length)')return '模型输出达到长度上限，JSON 被截断；本次未保存生成内容。';
 if(message==='AI response envelope invalid')return '模型接口返回结构不兼容，缺少 choices/message/content。';
 if(message==='AI response content empty or not text')return '模型接口没有返回文本内容。';
 return message;
}
export async function campusApi(path, data) {
  if (!['http:', 'https:'].includes(location.protocol)) {
    throw new Error('离线游戏仍可继续。校史与实时论坛需要本地服务，请运行 python server.py，再打开 http://127.0.0.1:8780。');
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      method: data === undefined ? 'GET' : 'POST',
      headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
      body: data === undefined ? undefined : JSON.stringify(data),
      signal: controller.signal,
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) throw new Error(campusError(result?.error) || `校园服务暂不可用（${response.status}）`);
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('校园服务响应超时。请刷新状态确认，勿重复提交。');
    if (error instanceof TypeError) throw new Error('无法连接校园服务；不影响继续审阅。请确认本地服务已启动。');
    throw error;
  } finally { clearTimeout(timeout); }
}
