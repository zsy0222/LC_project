"""一键启动脚本：自动初始化数据库 + 种子数据，启动 FastAPI 服务"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path 中
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Windows 终端强制 UTF-8 编码（避免 emoji 输出报错）
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    import uvicorn
    from src.config import HOST, PORT

    print("=" * 60)
    print("🌱  校园低碳回收全路径追踪系统 (LC_project)")
    print("   基于 AI 识别与批次化管理的回收闭环 Demo")
    print("=" * 60)
    print()
    print(f"📍  API 文档:   http://{HOST}:{PORT}/docs")
    print(f"🏠  系统首页:   http://{HOST}:{PORT}/")
    print()
    print("   未登录可查看排行榜，登录后使用投递/去向功能")
    print()
    print("💡  数据库与种子数据将在首次请求时自动初始化")
    print("=" * 60)

    uvicorn.run(
        "src.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
