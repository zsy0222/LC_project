"""AI 识别接口 + 图片上传"""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..config import UPLOAD_DIR
from ..schemas import PredictResp
from ..services.ai_service import predict_image, ai_status, compute_photo_hash

router = APIRouter(tags=["ai"])


@router.get("/ai/status")
def status():
    return ai_status()


@router.post("/predict", response_model=PredictResp)
async def predict(file: UploadFile = File(...)):
    """AI 识别接口：上传图片 → 返回品类/完整度/推荐路径/置信度"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片内容为空")

    try:
        result = predict_image(image_bytes)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"AI 识别失败: {e}") from e

    return PredictResp(**result)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """上传图片到本地存储，返回可访问 URL"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    ext = Path(file.filename or "").suffix or ".jpg"
    name = f"{uuid4().hex}{ext}"
    target = UPLOAD_DIR / name
    target.write_bytes(await file.read())
    return {"url": f"/uploads/{name}"}


@router.post("/photo/hash")
async def photo_hash(file: UploadFile = File(...)):
    """计算图片感知哈希，用于前端提前判断相似度"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片内容为空")
    try:
        h = compute_photo_hash(image_bytes)
        return {"hash": h}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"哈希计算失败: {e}") from e
