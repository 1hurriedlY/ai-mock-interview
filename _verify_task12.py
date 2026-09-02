"""任务 12 验证脚本：报告导出（DOCX + PDF）。

- 造一个真实可查的会话+报告（含五维/匹配/建议/表情数据），归属测试用户
- 走路由导出 docx / pdf → 文件落盘 → 下载接口可读
- 越权 403、报告不存在 404、非法格式 400

运行：.venv/Scripts/python.exe _verify_task12.py
"""
import _utf8_bootstrap  # noqa: F401
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------- 0. 环境自检 ----------
import reportlab  # noqa: F401
import docx  # noqa: F401

from app.services import export_service

print("[0] reportlab / python-docx 已安装")

# ---------- 1. 注册登录 ----------
USER = {"username": "task12_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("[1] 登录成功")

# ---------- 2. 造一份真实报告（模拟已完成面试的落库数据） ----------
from app.database import SessionLocal
from app.models import InterviewReport, InterviewSession, User

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "task12_user").first()
    session = InterviewSession(
        user_id=user.id,
        job_title="Python 后端工程师",
        interviewer_role="technical",
        resume_text="",
        status="completed",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    report = InterviewReport(
        session_id=session.id,
        summary="候选人基础扎实，对 Redis 缓存与消息队列有真实项目经验，表达条理清晰。",
        overall_score=82,
        dimensions=json.dumps(
            {"专业技能": 85, "沟通表达": 80, "逻辑思维": 84, "项目经验": 86, "岗位匹配": 78},
            ensure_ascii=False,
        ),
        match_analysis=json.dumps(
            {
                "match_level": "高",
                "reason": "技术栈与岗位高度契合，秒杀项目体现了高并发实战能力",
                "strengths": ["Redis 预扣库存方案考虑到了超卖", "能主动用 MQ 削峰"],
                "gaps": ["对分布式事务细节阐述不足"],
            },
            ensure_ascii=False,
        ),
        suggestions=json.dumps(
            ["补充分布式事务（Seata/TCC）的实践细节", "准备一个线上故障排查的案例"],
            ensure_ascii=False,
        ),
        expression_analysis=json.dumps(
            {
                "comment": "整体平静自信，深挖时偶有皱眉但能稳住思路",
                "highlights": ["提到项目成果时明显更有感染力"],
            },
            ensure_ascii=False,
        ),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    report_id = report.id
    print(f"[2] 测试报告已落库 report_id={report_id}（会话 {session.id}）")
finally:
    db.close()

# ---------- 3. 导出 DOCX / PDF ----------
for fmt in ("docx", "pdf"):
    r = client.post(f"/api/report/{report_id}/export", params={"format": fmt}, headers=HEADERS)
    assert r.status_code == 200, (fmt, r.text)
    info = r.json()
    assert info["format"] == fmt and info["report_id"] == report_id
    assert info["url"].endswith(f"?format={fmt}")
    assert info["size"] > 0
    path = export_service.export_path(report_id, fmt)
    assert path.exists(), f"{fmt} 文件未落盘"
    print(f"[3] 导出 {fmt.upper()} 成功：{path.name}（{info['size']} 字节）")

# 重复导出幂等（覆盖同名文件，仍 200）
r = client.post(f"/api/report/{report_id}/export", params={"format": "docx"}, headers=HEADERS)
assert r.status_code == 200, r.text
print("[4] 重复导出幂等通过")

# ---------- 4. 文件内容自检 ----------
from pathlib import Path

from app import config

docx_path = config.EXPORT_DIR / f"report_{report_id}.docx"
pdf_path = config.EXPORT_DIR / f"report_{report_id}.pdf"

# DOCX 可被 python-docx 正常读回
from docx import Document

doc = Document(str(docx_path))
all_text = "\n".join(p.text for p in doc.paragraphs)
for kw in ("综合得分", "五维能力评分", "专业技能", "岗位匹配", "改进建议", "表情表现分析", "Redis"):
    assert kw in all_text, f"DOCX 缺少关键内容：{kw}"
print("[5] DOCX 内容自检通过（含中文与报告各区块）")

# PDF 以 %PDF 开头且非空
pdf_bytes = Path(pdf_path).read_bytes()
assert pdf_bytes.startswith(b"%PDF"), "PDF 头不正确"
assert len(pdf_bytes) > 1000, "PDF 文件过小"
print("[6] PDF 文件头自检通过（%PDF 头，文件 {} 字节）".format(len(pdf_bytes)))

# ---------- 5. 下载接口 ----------
for fmt in ("docx", "pdf"):
    r = client.get(f"/api/report/{report_id}/download", params={"format": fmt}, headers=HEADERS)
    assert r.status_code == 200, r.text
    assert len(r.content) > 0
    ctype = r.headers["content-type"]
    assert (fmt == "docx" and "wordprocessingml" in ctype) or (fmt == "pdf" and "application/pdf" in ctype), ctype
    print(f"[7] 下载 {fmt.upper()} 通过（content-type={ctype}）")

# ---------- 6. 越权 / 不存在 / 非法格式 ----------
USER2 = {"username": "task12_user2", "password": "secret123"}
client.post("/api/auth/register", json=USER2)
r = client.post("/api/auth/login", json=USER2)
TOKEN2 = r.json()["access_token"]
r = client.post(f"/api/report/{report_id}/export", params={"format": "docx"},
                headers={"Authorization": f"Bearer {TOKEN2}"})
assert r.status_code == 403, r.text
print("[8] 越权导出拦截 403 通过")

r = client.post("/api/report/99999999/export", params={"format": "docx"}, headers=HEADERS)
assert r.status_code == 404, r.text
print("[9] 报告不存在返回 404 通过")

r = client.post(f"/api/report/{report_id}/export", params={"format": "xls"}, headers=HEADERS)
assert r.status_code == 400, r.text
print("[10] 非法格式返回 400 通过")

# 未认证
r = client.get(f"/api/report/{report_id}/download", params={"format": "docx"})
assert r.status_code == 401, r.text
print("[11] 未认证访问 401 通过")

print("== 任务 12 验证全部通过 ==")
