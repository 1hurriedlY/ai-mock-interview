"""临时清理脚本：删除 task9 上一轮产生的脏报告（session 6/7）。"""
import _utf8_bootstrap  # noqa: F401
import sys

sys.path.insert(0, "backend")

from app.database import SessionLocal
from app.models import InterviewReport, InterviewSession

db = SessionLocal()
try:
    for sid in (6, 7):
        r = db.query(InterviewReport).filter(InterviewReport.session_id == sid).first()
        if r:
            db.delete(r)
            db.commit()
            print("已删除脏报告 id=", r.id, "session=", sid)
        s = db.get(InterviewSession, sid)
        if s:
            s.status = "in_progress"
            s.ended_at = None
            db.commit()
            print("已重置会话状态", sid)
finally:
    db.close()
