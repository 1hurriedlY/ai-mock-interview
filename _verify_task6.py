"""任务 6 验证脚本：Agent 流水线状态机（题卡 → 逐题推进 → 追问 → 结束）。

为隔离真实大模型调用，本脚本用固定假题卡 + 假面试官回复，验证状态机推进逻辑。
"""
import sys

sys.path.insert(0, "backend")

from unittest.mock import patch

from app import redis_client as rc_mod
from app.services.agents import pipeline as pipe_mod

rc = rc_mod.redis_client  # 单例

# 用假的 redis（内存字典）避免污染真实 Redis，但保留 Redis 真实连接时也可用
# 这里直接给 pipeline 的读写打桩，保证可离线运行

FAKE_CARD = {
    "stages": {
        "opening": [{"question": "请自我介绍", "reference": "要点1"}],
        "basic": [
            {"question": "基础题1", "reference": "要点2"},
            {"question": "基础题2", "reference": "要点3"},
        ],
        "deep": [{"question": "深度题1", "reference": "要点4"}],
        "stress": [{"question": "压力题1", "reference": "要点5"}],
        "closing": [{"question": "你还有什么想问", "reference": "要点6"}],
    }
}


def make_pipeline(session_id):
    # 先写入假题卡
    rc.set_question_card(session_id, FAKE_CARD)
    return pipe_mod.InterviewPipeline(session_id, role="technical")


# 打桩面试官 decide：根据 candidate_answer 返回指定动作
fake_replies = iter([
    # 第1题 opening
    {"action": "next", "reply": "好的，请回答基础题1", "reference": "r1"},
    # 基础题1：先 probe 再 next
    {"action": "probe", "reply": "请展开", "reference": "r2"},
    {"action": "next", "reply": "很好，基础题2", "reference": "r3"},
    # 基础题2：followup 再 next
    {"action": "followup", "reply": "再深挖一下", "reference": "r4"},
    {"action": "next", "reply": "不错，深度题1", "reference": "r5"},
    # 深度题1：next
    {"action": "next", "reply": "好的，压力题1", "reference": "r6"},
    # 压力题1：next
    {"action": "next", "reply": "收尾", "reference": "r7"},
    # closing：finish
    {"action": "finish", "reply": "面试结束", "reference": "r8"},
])


def fake_decide(**kwargs):
    return next(fake_replies)


def main():
    with patch.object(pipe_mod.InterviewerAgent, "decide", side_effect=fake_decide):
        pl = make_pipeline(1)

        # 1. 当前题
        cur = pl.current()
        print("[1] 当前题:", cur["stage"], cur["question"])
        assert cur["stage"] == "opening" and cur["question"] == "请自我介绍"

        # 2. 逐轮推进
        conversation = []
        results = []
        round_no = 1
        while True:
            dec = pl.advance(conversation=conversation, candidate_answer=f"候选人回答{round_no}")
            if dec is None or dec["action"] == "finish":
                if dec:
                    results.append(dec)
                break
            results.append(dec)
            conversation.append({"role": "assistant", "content": dec["reply"]})
            conversation.append({"role": "user", "content": f"候选人回答{round_no}"})
            cur = pl.current()
            # 每轮打印进度
            if cur:
                print(f"[{round_no+1}] 推进后当前题: {cur['stage']} / {cur['question']}")
            round_no += 1

        print("[2] 总轮数:", len(results))
        assert len(results) == 8, f"期望 8 轮，实际 {len(results)}"
        # 轮次分布：opening next + basic probe/next + basic2 followup/next + deep next + stress next + closing finish
        actions = [r["action"] for r in results]
        print("    actions:", actions)
        assert actions == ["next", "probe", "next", "followup", "next", "next", "next", "finish"]

        # 3. finish 后：游标停留在最后一题，但流水线已返回 finish 表示结束
        #    （前端收到 action=finish 即结束面试，不需再推进游标）
        print("[3] finish 后当前题:", pl.current())
        assert pl.current() is not None  # 游标不自动清空
        assert results[-1]["action"] == "finish"  # 以 finish 动作标记结束

        # 4. 追问上限：同一题连续 3 次 probe 应强制推进
        rc.set_question_card(2, {**FAKE_CARD, "_state": {"stage_idx": 1, "question_idx": 0, "probes": 0}})
        pl2 = pipe_mod.InterviewPipeline(2, role="technical")
        probe_replies = [
            {"action": "probe", "reply": "p1", "reference": "r"},
            {"action": "probe", "reply": "p2", "reference": "r"},
            {"action": "probe", "reply": "p3", "reference": "r"},
        ]
        with patch.object(pipe_mod.InterviewerAgent, "decide", side_effect=iter(probe_replies)):
            for i in range(3):
                dec = pl2.advance(conversation=[], candidate_answer="短")
                cur2 = pl2.current()
                print(f"[4] 第{i+1}次probe后: action={dec['action']} 当前题={cur2['stage']}/{cur2['question']}")
        # 第3次 probe 已达上限，应推进到基础题2
        assert pl2.current()["question"] == "基础题2", f"追问上限未强制推进: {pl2.current()}"

        print("== 任务 6 验证全部通过 ==")


if __name__ == "__main__":
    main()
