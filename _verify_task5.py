"""任务 5 验证脚本：面试官 Agent 追问/节奏/参考要点（真实调用通义千问）。"""
import sys

sys.path.insert(0, "backend")

from app.services.agents.interviewer_agent import InterviewerAgent

agent = InterviewerAgent()

# 场景 1：回答充分 → 应 next（推进下一题）
print("[1] 回答充分 → 期望 next")
r1 = agent.decide(
    role="technical",
    stage_label="基础题",
    current_question="什么是 Python 的 GIL？它有什么影响？",
    current_reference="解释 GIL 机制及对多线程的影响",
    next_question="你在项目中如何解决多线程性能问题？",
    conversation=[
        {"role": "assistant", "content": "请先做个自我介绍。"},
        {"role": "user", "content": "我是有三年经验的 Python 后端工程师。"},
    ],
    candidate_answer=(
        "GIL 是 CPython 解释器里的全局解释器锁，同一时刻只允许一个线程执行 Python 字节码。"
        "它对 CPU 密集型任务有负面影响，因为多线程无法真正并行；但对 IO 密集型任务影响不大。"
        "我一般用多进程或者 asyncio 来规避。"
    ),
)
print("   action:", r1["action"], "| reply:", r1["reply"][:40])
assert r1["action"] == "next", f"期望 next 实际 {r1['action']}"

# 场景 2：回答过短含糊 → 应 probe
print("[2] 回答过短 → 期望 probe")
r2 = agent.decide(
    role="technical",
    stage_label="深度题",
    current_question="你们订单系统怎么保证支付回调的幂等性？",
    current_reference="幂等键/状态机/数据库唯一约束",
    next_question="谈一下你对分布式事务的理解",
    conversation=[
        {"role": "assistant", "content": "我们进入深度题环节。"},
        {"role": "user", "content": "好的。"},
    ],
    candidate_answer="就是判断一下状态，避免重复处理。",
)
print("   action:", r2["action"], "| reply:", r2["reply"][:40])
assert r2["action"] == "probe", f"期望 probe 实际 {r2['action']}"

# 场景 3：回答提到方案但未展开 → followup 或 probe 均合理（中间地带）
print("[3] 提到方案未展开 → 期望 followup 或 probe")
r3 = agent.decide(
    role="technical",
    stage_label="深度题",
    current_question="Redis 的缓存穿透怎么解决？",
    current_reference="布隆过滤器/空值缓存/接口限流",
    next_question="缓存雪崩呢？",
    conversation=[{"role": "assistant", "content": "请介绍缓存穿透的解决思路。"}],
    candidate_answer="可以用布隆过滤器，也可以用缓存空值的方法。",
)
print("   action:", r3["action"], "| reply:", r3["reply"][:40])
assert r3["action"] in ("followup", "probe"), f"期望 followup/probe 实际 {r3['action']}"

# 场景 4：回答跑题过长 → reply 应体现打断引导
print("[4] 回答跑题 → reply 应拉回本题")
r4 = agent.decide(
    role="technical",
    stage_label="基础题",
    current_question="请解释一下 RESTful API 的设计原则。",
    current_reference="资源命名/HTTP 动词/状态码/无状态",
    next_question="你用过哪些版本管理工具？",
    conversation=[{"role": "assistant", "content": "请谈谈 RESTful API 设计原则。"}],
    candidate_answer=(
        "这个啊，我最近在看的那个电视剧特别好，讲的是一群程序员创业的故事，"
        "他们用的是什么技术栈……（说了 500 字）……所以我觉得沟通很重要，团队氛围要好，"
        "然后周末我去爬山，锻炼身体，保持精力充沛……"
    ),
)
print("   action:", r4["action"], "| reply:", r4["reply"][:50])
assert "打断" in r4["reply"] or "回到" in r4["reply"] or "问题" in r4["reply"], f"reply 未拉回本题: {r4['reply']}"
assert r4["reference"], "缺少参考要点"

# 场景 5：最后一道题 + 回答充分 → 应 finish
print("[5] 最后一题回答充分 → 期望 finish")
r5 = agent.decide(
    role="HR",
    stage_label="收尾反问",
    current_question="你还有什么想问我们的吗？",
    current_reference="候选人主动提问表现积极性",
    next_question=None,
    conversation=[
        {"role": "assistant", "content": "面试接近尾声。"},
        {"role": "user", "content": "我想了解团队的技术栈和成长路径。"},
    ],
    candidate_answer=(
        "我想请问贵团队目前在技术方向上最大的挑战是什么？"
        "同时我也比较关注新人的培养机制，想了解有没有定期的技术分享。"
    ),
)
print("   action:", r5["action"], "| reply:", r5["reply"][:40])
assert r5["action"] == "finish", f"期望 finish 实际 {r5['action']}"

print("== 任务 5 验证全部通过 ==")
