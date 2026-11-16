"""仅用于本次明确授权的离线公开修订，不调用模型，不伪造审查。"""
import copy
import json
from pathlib import Path
import author
import runtime as r

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'tools/successful-run.json'
p = json.loads(path.read_text(encoding='utf-8'))
a = p['author']
if 'manual_revision' in a:
    raise SystemExit('已修订，禁止重复覆盖历史')
history = copy.deepcopy(a)
statements = {
's3': '各位评委好，我是苏晚棠，社会学专业研一学生。本科就读于外校师范类院校，毕业绩点约3.8/4.0，专业前5%；研究生阶段，我也在学习把扎实的访谈转化为更清楚的分析。我参与城市更新与社区治理课题半年，承担联络、访谈和转录，尚无署名成果；在学院研究生会学术部组织过两次读书会，本科还做过两年周末阅读支教。比起把经历列满，我更希望说明自己如何从认真倾听走向独立判断。与亦航相处，让我意识到关心不只是陪伴，也包括把安排说清楚。他在工作室给我留空桌和插座，我在他赶模型时听他讲设计；我们也慢慢学会，不把每次散步都变成我的田野。我申请优秀情侣奖，是希望呈现两个人如何在各自的专业道路上成长，并为对方留出位置。',
's4': '各位评委好，我是郑亦航，建筑学专业大二学生，学制五年。我的绩点约3.2/4.0，年级排名中游，设计课还不够稳定；《建筑构造》一类课程保持在80分出头。做模型和观察街巷，是我理解建筑最直接的方式。我在学院足球队踢边后卫，与高中同学组乐队弹贝斯，曾在校园开放日演出，也在大一参与过迎新晚会执行。这些经历让我逐渐明白，热心答应不等于真正完成，投入也需要安排。晚棠做访谈时的耐心，让我开始认真解释自己为什么这样设计，而不只说好看。她赶转录时，我给她留工位；我赶模型时，她来听我说进度。我们并非从不冲突，但已经学着提前说明忙碌，不让对方一直等。我希望以尚在成长的自己参评，说明互相支持可以很具体：各自做好自己的事，也认真回应对方。'
}
chronos = copy.deepcopy(a['results']['chronos'])
for person in chronos['people'].values():
    person.pop('form', None)
chronos['summary'] = '两人分别收到通知，经历犹豫、讨论和各自忙碌后，最终于5月4日明确同意并报名。Chronos只记录填表报名剧情，正式陈述由独立报名Muse阶段负责。'
chronos['registration'].pop('withdrawn_on', None)
a['results']['chronos'] = chronos
a['results']['application'] = {'statements': statements, 'metadata': {'both_authorized': True, 'privacy': '沿用原提交授权；公开展示仍未授权；手工修订不冒充学生重新签署', 'submitted_on': chronos['registration']['submitted_on']}}
a['announcement'] = author.notice()
a['game_snapshot'] = author.make_game(a)
a['game_snapshot']['submission']['submitted_at_system'] = history['game_snapshot']['submission']['submitted_at_system']
a['nomination']['snapshot_digest'] = r.digest(a['game_snapshot'])
# 保留段落ID，旧态度反应仍可定位；以下只使用已披露履历作为启发。
texts = {
'beat2': '各位评委好，我叫苏晚棠，社会学研一。我一开始以为，把访谈认真做完就够了；后来发现，把听到的生活讲清楚，可能才是更难的部分。',
'beat3': '大家好，我是郑亦航，建筑学大二，五年制。我大概正相反，方案还没做完，解释已经想了三套。今天我尽量少绕，先讲自己做过什么。',
'beat4': '我们一个习惯先听，一个总想先说。今天也试着把这个顺序搭好。',
'beat6': '我本科毕业时绩点约3.8，专业前5%。到了研究生，《社会研究方法》拿了B+，其他课程在85分以上。那个B+让我有点不服气，也让我开始问：材料多，是否真的等于分析清楚？',
'beat7': '我跟着导师做城市更新与社区治理课题，半年里主要负责联络、访谈和转录，目前还没有署名成果。学术部的两次读书会，也让我练习把问题讲短一点，而不是把每条笔记都读出来。',
'beat8': '本科两年的周末阅读支教，是另一种练习。孩子不一定按教案回答，你得先听懂他为什么那样想。其实做访谈也有一点像，只是我还在学。',
'beat9': '我的成绩没有她那么整齐，绩点约3.2，年级中游。设计课会起伏，《建筑构造》稳定在80出头。以前我爱说评图看运气，现在觉得，方案说不清楚的地方，还是得自己补。',
'beat10': '我在足球队踢边后卫，也和两个高中同学组乐队，弹贝斯。去年开放日演了两首。说来挺巧，两个位置都不能只顾自己往前冲，总得听见队友。',
'beat11': '大一我做过迎新晚会执行，后来退出了，时间真不够用。我还喜欢骑车拍老街，骑楼、栏杆都拍。有时候照片挺好看，一问为什么好看，我就得重新想。',
'beat13': '晚棠：你刚才把“说不清楚”讲了两次。亦航：因为确实没全想清楚。晚棠：这个我倒是很熟悉。',
'beat14': '我做访谈可以听很久，轮到解释自己的判断，却容易把句子越讲越长。听他讲一个方案时，我会追问：你最想留下的，到底是哪一个地方？这也像是在问自己。',
'beat15': '她这个问题很厉害。我本来能讲三分钟，后来得先选一句最重要的。反过来，她纠结一段材料时，我就想说：先讲你看见了什么，别急着把整座城都装进去。',
'beat17': '晚棠：不是谁替谁给答案。亦航：是有人愿意再问一句，也愿意听你把话说完。',
'beat18': '如果各位想问我的田野工作，我愿意从联络、访谈和转录这些具体环节谈起。哪些判断还没成熟，我也会说出来。',
'beat19': '如果问建筑，我可以从模型和街巷观察讲。足球和乐队也能聊，不过贝斯今天没带，先不临时加节目了。',
'beat20': '我还没想清楚的事情很多。但我希望自己的认真，不只是把材料攒起来，也能让别人更容易理解。',
'beat21': '我希望自己的热心，也别总停在一句“没问题”。答应了什么，最后做到了什么，这个比说得热闹重要。',
'beat23': '我们都还在练习。一个少绕一点，一个多停一下。',
'beat24': '我申请这个奖，不是因为我们已经把生活安排得很好，而是这段关系让我更愿意看见自己的盲点。',
'beat25': '我也是。她没有替我完成设计，却让我开始认真回答，自己为什么要这样做。',
'beat26': '各自向前，也给对方留一个能说话、能被听见的位置。',
'beat28': '谢谢各位评委，我们愿意听听大家的问题。'
}
script = a['results']['script']
script['title'] = '各自向前，彼此接话'
for scene in script['scenes']:
    for beat in scene['beats']:
        if beat['id'] in texts:
            beat['text'] = texts[beat['id']]
        else:
            beat['text'] = '两人整理各自的材料，停顿后看向对方，示意接续。'
        beat['action'] = '整理材料，面向评委，自然接续同伴的话。'
        beat['framing'] = 'staging'
script['backstage'].append('2026-11-16操作者手工修订：具体互动为已披露专业履历启发的宣传加工，不新增真实经历，不冒充模型审查。')
for stage in ('chronos', 'application', 'script'):
    a['locks'][stage] = r.digest(a['results'][stage])
a['manual_revision'] = {'actor': 'operator', 'date': '2026-11-16', 'model_reviewed': False, 'reason': '用户授权手工修订公开报名、剧情职责和答辩；保留原始人物及全部历史审查，不伪造C_Muse/C_Chronos批准', 'approved_digests': {stage: a['locks'][stage] for stage in ('chronos', 'application', 'script')}, 'original_author': history}
a['logs'].append({'time': author.now(), 'kind': 'manual_public_revision', 'task': None, 'detail': '公开内容人工修订，未调用模型；原author及历史审查保存在manual_revision.original_author'})
author.Engine().validate_project(a)
path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding='utf-8')
print('公开结果修订完成；原人物与历史保留，模型审查未伪造')
