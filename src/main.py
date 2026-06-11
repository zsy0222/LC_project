"""FastAPI 入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, WEB_DIR, UPLOAD_DIR
from .database import init_db
from .seed import seed_all
from .api import scan, predict, submission, batch, user, rank, reward, activity, auth


def create_app() -> FastAPI:
    app = FastAPI(
        title="LC_project · 校园低碳回收追踪",
        description="基于 AI 识别与批次化管理的回收闭环 Demo",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 初始化数据库与种子数据
    init_db()
    seed_all()

    # 静态文件
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
    app.mount("/image", StaticFiles(directory=str(BASE_DIR / "image")), name="image")
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

    # 业务路由
    for r in (scan.router, predict.router, submission.router,
              batch.router, user.router, rank.router, reward.router, activity.router, auth.router):
        app.include_router(r, prefix="/api")

    # 首页
    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/favicon.ico")
    def favicon():
        # 返回透明 1x1 像素 ICO（避免 404）
        return Response(
            content=b"\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x0b\x00\x00\x00\x16\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            media_type="image/x-icon",
        )

    return app


app = create_app()
