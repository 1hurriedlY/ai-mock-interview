"""验证脚本 UTF-8 引导：在 import 任何业务模块前，先把 stdout/stderr 切到 UTF-8。

Windows 终端/管道默认 GBK（代码页 936），Python 的 sys.stdout 按 GBK 编码，
中文字符串（如验证脚本的 print 输出）在 bash 管道里就变成乱码。

本模块放在每个 _verify_*.py 的最顶部 import（必须在 sys.path / app 之前）：
    import _utf8_bootstrap  # noqa: F401
"""
import sys

# 优先用 Python 3.7+ 的 UTF-8 模式，其次手动重建 stdout/stderr
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

import io  # noqa: E402

if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if not isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
