"""任务 1 验证脚本：验证后端骨架模块导入与 JWT 工具。"""
import sys

sys.path.insert(0, "backend")

# 1. 关键依赖导入
import jwt
import dotenv
import fastapi
import sqlalchemy
import pymysql
import redis
print("[1] 依赖导入 OK：PyJWT / python-dotenv / fastapi / sqlalchemy / pymysql / redis")

# 2. 后端骨架模块导入
from app import config
from app import database
from app import models
from app import auth
from app import redis_client
print("[2] 骨架模块导入 OK：config / database / models / auth / redis_client")

# 3. JWT 签发与校验
token = auth.create_access_token(user_id=1)
user_id = auth.decode_access_token(token)
assert user_id == 1, "JWT 解码用户 id 不匹配"
print(f"[3] JWT 签发与校验 OK：token 前20位={token[:20]}..., 解码 user_id={user_id}")

# 4. 密码哈希与校验
hashed = auth.hash_password("test123456")
assert auth.verify_password("test123456", hashed)
assert not auth.verify_password("wrong", hashed)
print("[4] 密码哈希与校验 OK")

# 5. 主应用可加载
from app.main import app
print(f"[5] 主应用加载 OK：title={app.title}, 路由数={len(app.routes)}")

print("== 任务 1 验证全部通过 ==")
