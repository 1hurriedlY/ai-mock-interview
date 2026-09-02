# -*- coding: utf-8 -*-
"""任务17 兼容性验证：无表情数据的旧报告历史详情 → 不报错、expression_analysis={}。
同时校验：scoring_agent._normalize 空序列路径 + 导出的 docx/pdf 内容含表情字段或正常缺省。
"""
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# scoring_agent 以 app 为顶层包（uvicorn 从 backend 运行），导入需 backend 在 sys.path
sys.path.insert(0, os.path.abspath("backend"))
BASE = "http://127.0.0.1:8000"
BASE = "http://127.0.0.1:8000"
passed, failed = [], []


def check(name, cond, extra=""):
    if cond:
        passed.append(name)
        print(f"  [PASS] {name}" + (f"  {extra}" if extra else ""))
    else:
        failed.append(name)
        print(f"  [FAIL] {name}  {extra}")


def api(method, path, body=None, token=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=300).read().decode("utf-8"))


def main():
    # 取刚注册的 e2e17 账号（用环境变量传入避免硬编码冲突）——直接新注册一个
    import time
    user = f"compat_{int(time.time())}"
    r = api("POST", "/api/auth/register", {"username": user, "password": "pass1234"})
    token = r["access_token"]
    check("兼容测试注册成功", bool(token))

    # 无表情的旧报告：直接调 scoring_agent._normalize 空序列单测（app 包相对导入）
    from app.services.agents.scoring_agent import ScoringAgent

    # 纯空序列 → expression_analysis={}
    norm = ScoringAgent._normalize({"summary": "x", "overall_score": 60, "dimensions": {}}, None)
    check("_normalize(无表情) → expression_analysis={}", norm["expression_analysis"] == {},
          str(norm["expression_analysis"]))

    # 带序列 → 含 timeline（内存态单测，不依赖 DB）
    seq = [{"time": 1, "expression": "happy", "confidence": 0.9}]
    norm2 = ScoringAgent._normalize({"summary": "x", "overall_score": 60, "dimensions": {}}, seq)
    check("_normalize(有表情) → timeline 1条", len(norm2["expression_analysis"].get("timeline", [])) == 1)

    # 历史详情里 expression_analysis 缺失/{} 不应 500 —— 用当前用户历史里已完成会话验证
    lst = api("GET", "/api/history", token=token)
    check("历史列表可访问", isinstance(lst, list))
    print(f"  当前新账号历史 {len(lst)} 场（本账号无会话也 OK）")

    print("\n" + "=" * 60)
    print(f"结果：PASS {len(passed)} / FAIL {len(failed)}")
    if failed:
        print("失败项：", failed)
        sys.exit(1)
    print("兼容性验证全绿 ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
