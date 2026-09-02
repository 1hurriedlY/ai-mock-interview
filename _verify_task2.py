"""任务 2 验证脚本：用 FastAPI TestClient 测试认证接口（注册/登录/me + JWT）。"""
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

# TestClient 会触发 startup 建表（MySQL 需已启动）
with TestClient(app) as client:
    # 1. 健康检查
    r = client.get("/api/health")
    print("[1] 健康检查:", r.status_code, r.json())
    assert r.status_code == 200

    # 2. 注册新用户
    username = "tester"
    password = "test123456"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    print("[2] 注册:", r.status_code, r.json().get("username"), "token长度=", len(r.json().get("access_token", "")))
    assert r.status_code == 201
    token = r.json()["access_token"]

    # 3. 重复注册应返回 409
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    print("[3] 重复注册:", r.status_code, r.json())
    assert r.status_code == 409

    # 4. 错误密码登录应返回 401
    r = client.post("/api/auth/login", json={"username": username, "password": "wrongpass"})
    print("[4] 错误密码登录:", r.status_code, r.json())
    assert r.status_code == 401

    # 5. 正确登录
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    print("[5] 正确登录:", r.status_code, "token长度=", len(r.json().get("access_token", "")))
    assert r.status_code == 200
    login_token = r.json()["access_token"]

    # 6. 无 token 访问 /me 应返回 401
    r = client.get("/api/auth/me")
    print("[6] 无 token /me:", r.status_code, r.json())
    assert r.status_code == 401

    # 7. 带 token 访问 /me（注册返回的 token）
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    print("[7] 注册token /me:", r.status_code, r.json().get("username"))
    assert r.status_code == 200
    assert r.json()["username"] == username

    # 8. 带登录 token 访问 /me（登录返回的 token）
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    print("[8] 登录token /me:", r.status_code, r.json().get("username"))
    assert r.status_code == 200

print("== 任务 2 验证全部通过 ==")
