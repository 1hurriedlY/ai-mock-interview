"""创建数据库 interview 并建表（用 pymysql 直连 MySQL，执行 interview_schema.sql）。

说明：
- 仅创建库与表，不影响已有数据
- 表结构由 interview_schema.sql 定义，与后端 ORM 保持一致
"""
import pymysql
from pathlib import Path

MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "123456"
DB_NAME = "interview"

schema_path = Path(__file__).parent / "interview_schema.sql"

def main() -> None:
    # 先连接 MySQL（不指定库），创建 database
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"[OK] 数据库 {DB_NAME} 就绪")
        conn.commit()
    finally:
        conn.close()

    # 连接目标库，执行建表脚本
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET NAMES utf8mb4")
        statements = split_sql(schema_path.read_text(encoding="utf-8"))
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
                print(f"[OK] 执行: {stmt.splitlines()[0][:60]}")
        conn.commit()
        print("== 建表完成 ==")
    finally:
        conn.close()


def split_sql(sql: str) -> list[str]:
    """按分号拆分 SQL，忽略 -- 注释行和 USE 语句。"""
    statements = []
    buf = []
    for raw_line in sql.splitlines():
        line = raw_line.strip()
        if line.startswith("--") or not line:
            continue
        if line.upper().startswith("USE "):
            continue
        buf.append(line)
        if line.endswith(";"):
            stmt = " ".join(buf).rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            buf = []
    if buf:
        stmt = " ".join(buf).strip()
        if stmt:
            statements.append(stmt)
    return statements


if __name__ == "__main__":
    main()
