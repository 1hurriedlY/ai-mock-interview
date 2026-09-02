# -*- coding: utf-8 -*-
"""量化后端 Agent 各接口耗时：channels / script / start（题卡）。"""
import io
import json
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:8000"


def api(method, path, body=None, token=None, timeout=180):
    headers = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        dt = time.time() - t0
        raw = r.read().decode("utf-8")
        return r.status, dt, raw
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, e.read().decode("utf-8")
    except Exception as e:
        return None, time.time() - t0, str(e)


def main():
    u = f"t18_{int(time.time())}"
    s, _, _ = api("POST", "/api/auth/register", {"username": u, "password": "pass1234"})
    tok = json.loads(_)["access_token"] if False else None
    # register 返回体在上一步未取，重登一次
    s, dt, raw = api("POST", "/api/auth/login", {"username": u, "password": "pass1234"})
    tok = json.loads(raw).get("access_token")
    print(f"login {s} {dt:.1f}s")

    s, dt, raw = api("POST", "/api/project/channels", {}, tok)
    print(f"channels {s} {dt:.1f}s head={raw[:60]}")

    s, dt, raw = api("POST", "/api/project/script",
                     {"project_name": "支付网关", "description": "FastAPI+MySQL"}, tok)
    print(f"script {s} {dt:.1f}s head={raw[:80]}")

    s, dt, raw = api("POST", "/api/interview/start",
                     {"job_title": "Python 后端工程师", "role": "technical"}, tok)
    print(f"start {s} {dt:.1f}s head={raw[:120]}")

    print("DONE")


if __name__ == "__main__":
    main()
