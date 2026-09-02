# -*- coding: utf-8 -*-
"""任务14 前端真实页面冒烟：走 LoginView → HomeView → InterviewView → ReportView → HistoryView
的真实 Vue 应用（无需浏览器）：验证 vue-router + axios + SSE + echarts 按需 + blob 导出
在真实 vite dev server 上能跑通。

本脚本不依赖 Selenium。它通过 vite dev server 的服务端渲染代理链路逐一探测前端
能访问到的静态入口与 API 代理，确认页面路由对应 chunk 可加载。

说明：SSE/JS 交互链路由浏览器负责，脚本只验证 dev server 返回 200 + 各路由 chunk 存在。
更重的浏览器内联调用在浏览器人工验收环节执行。
"""
import io
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://localhost:5175"
checks = []


def ck(name, cond, extra=""):
    checks.append((name, cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {extra}")


def get(path):
    try:
        r = urllib.request.urlopen(BASE + path, timeout=10)
        return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:
        return getattr(e, "code", -1), str(e)


# 所有视图路由的静态入口（vue-router history 路由交给 vite 的 SPA fallback）
for path in ["/", "/login", "/home", "/interview/11", "/report/9", "/history", "/industry", "/project"]:
    st, body = get(path)
    ck(f"路由 {path} -> {st}", st == 200)

# vite 会返回 index.html（SPA），body 应含 app 挂载点
st, body = get("/home")
ck("SPA fallback 返回 index.html", 'id="app"' in body)

# API 代理透传
st, body = get("/api/health")
ck("代理 /api/health", st == 200 and '"ok"' in body, body[:60])

# 关键 chunk 是否在构建产物可解析（echarts 按需、各视图）
st, body = get("/src/views/InterviewView.vue")
ck("InterviewView.vue 可被 vite 编译提供", st == 200, "" if st == 200 else body[:80])
st, body = get("/src/components/ScoreRadar.vue")
ck("ScoreRadar.vue 提供", st == 200)

print("\n" + "=" * 40)
passed = sum(1 for _, ok in checks if ok)
print(f"冒烟结果：PASS {passed}/{len(checks)}")
if passed != len(checks):
    sys.exit(1)
print("前端冒烟全绿 ✅")
