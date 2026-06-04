"""Full API and logic tests - ASCII-safe output"""
import sys, os, json
sys.path.insert(0, r'C:\Users\chenm\Desktop\program\LC_project')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from src.database import init_db, SessionLocal
from src.seed import seed_all
from src.models import User, Point, Batch, Submission, ReuseItem, Notification

init_db()
seed_all()
db = SessionLocal()

errors = []

def check(desc, condition):
    if not condition: errors.append(desc)
    print(f"  {'[OK]' if condition else '[FAIL]'} {desc}")

print("=" * 60)
print("TEST 1: Seed data integrity")
print("=" * 60)
users = db.query(User).all()
check("14 users", len(users) == 14)
roles = {}
for u in users:
    roles.setdefault(u.role, []).append(u.nickname)
check("10 reusers", len(roles.get('reuser', [])) == 10)
check("3 students", len(roles.get('student', [])) == 3)
check("1 admin", len(roles.get('admin', [])) == 1)
points = db.query(Point).all()
check("4 points", len(points) == 4)
from src.config import TREATMENT_KNOWLEDGE
check("21 treatments", len(TREATMENT_KNOWLEDGE) == 21)
zg = db.query(Point).filter(Point.name == "郑钢教学楼").first()
check("Zhengang segment GPS", zg and ';' in zg.gps)

print()
print("=" * 60)
print("TEST 2: API endpoints")
print("=" * 60)
from fastapi.testclient import TestClient
from src.main import app
client = TestClient(app)

gets = [
    ("/api/users", 200),
    ("/api/points", 200),
    ("/api/ai/status", 200),
    ("/api/config/demo", 200),
    ("/api/rank", 200),
    ("/api/batches", 200),
    ("/api/knowledge/treatments", 200),
    ("/api/gallery", 200),
    ("/api/submission/cooldown?user_id=1&qr_code=PT-A03", 200),
    ("/api/submission/pending/1", 200),
    ("/api/user/1/profile", 200),
    ("/api/user/1/submissions", 200),
    ("/api/user/1/streak", 200),
    ("/api/user/1/tracking", 200),
    ("/api/user/1/reward-status", 200),
    ("/api/batch/FAKE/story", 404),
]
for url, exp in gets:
    r = client.get(url)
    check(f"GET {url}", r.status_code == exp)

print()
print("=" * 60)
print("TEST 3: Submission flow")
print("=" * 60)

# Food waste pending
r = client.post("/api/submission/pending", json={
    "user_id": 1, "waste_type": "外卖厨余",
    "category": "外卖厨余", "score": 0.85,
    "photo": "/uploads/test.png", "photo_hash": "abc123",
    "item_count": 1,
})
check("POST pending", r.status_code == 200)
food_sub_id = r.json()["id"] if r.status_code == 200 else None

# Confirm at Zhengang
if food_sub_id:
    r2 = client.post(f"/api/submission/{food_sub_id}/confirm", json={
        "user_id": 1, "user_lat": 32.057754, "user_lng": 118.774912,
        "qr_code": "PT-D04", "confirmed": True,
    })
    check("confirm submission", r2.status_code == 200)
    if r2.status_code == 200:
        csub = r2.json()
        check("confirm returns batch_id", csub["batch_id"].startswith("BATCH"))
        check("confirm co2 > 0", csub["co2_saved"] > 0)

# Cardboard at Software College
r3 = client.post("/api/submission", json={
    "user_id": 1, "qr_code": "PT-A03", "waste_type": "快递纸箱",
    "category": "快递纸箱", "grade": "完好", "score": 0.9,
    "photo": "/uploads/test2.png", "photo_hash": "def456",
    "item_count": 1, "user_lat": 32.060613, "user_lng": 118.773064,
})
check("POST submission cardboard", r3.status_code == 200)
if r3.status_code == 200:
    csub = r3.json()
    check("batch_id valid", csub["batch_id"].startswith("BATCH"))
    check("co2 > 0", csub["co2_saved"] > 0)
    check("streak field", csub["streak"] >= 0)

batches = client.get("/api/batches?status=pending").json()
check("pending batches exist", len(batches) > 0)

print()
print("=" * 60)
print("TEST 4: Claim + Reuse")
print("=" * 60)

if batches:
    bid = batches[0]["id"]
    shiwei = db.query(User).filter(User.nickname == "食监委").first()

    r4 = client.post("/api/batch/claim", json={
        "batch_id": bid, "reuser_id": shiwei.id, "destination": "厌氧消化工艺"
    })
    check("claim batch", r4.status_code == 200)

    db2 = SessionLocal()
    batch = db2.query(Batch).get(bid)
    check("claimed_by set", batch.claimed_by == shiwei.id)
    check("status = claimed", batch.status == "claimed")
    db2.close()

    r5 = client.post("/api/batch/reuse", json={
        "batch_id": bid, "reuser_id": shiwei.id,
        "product_photo": "/uploads/product.png", "product_desc": "",
    })
    check("reuse batch", r5.status_code == 200)

    db3 = SessionLocal()
    batch3 = db3.query(Batch).get(bid)
    check("status = done", batch3.status == "done")
    item = db3.query(ReuseItem).filter(ReuseItem.batch_id == bid).first()
    check("AI desc auto-filled", bool(item and item.product_desc and len(item.product_desc) > 10))
    notifs = db3.query(Notification).filter(Notification.batch_id == bid).all()
    check("notifications sent", len(notifs) > 0)
    db3.close()

    # Tracking
    r6 = client.get("/api/user/1/tracking")
    t = r6.json()
    check("tracking has items", len(t["items"]) > 0)

print()
print("=" * 60)
print("TEST 5: Claim exclusivity + Gallery")
print("=" * 60)

art = db.query(User).filter(User.nickname == "美术社").first()
r7 = client.post("/api/batch/reuse", json={
    "batch_id": bid, "reuser_id": art.id,
    "product_photo": "/uploads/art.png", "product_desc": "handmade",
})
# Batch is already "done", so it returns 400 (not claimable for reuse)
# If batch were still "claimed", it would return 403 (wrong reuser)
check("cross-user blocked", r7.status_code != 200)

r8 = client.get(f"/api/gallery?user_id=1")
g = r8.json()
check("gallery has items", len(g["items"]) > 0)

r9 = client.get("/api/user/1/reward-status")
rs = r9.json()
check("reward has current_stage", "current_stage" in rs)
check("reward has stage_image", "stage_image" in rs)
check("stage_image valid", rs["stage_image"].startswith("/checkin"))

print()
print("=" * 60)
print("TEST 6: Anti-cheat")
print("=" * 60)

# GPS too far
r10 = client.post("/api/submission", json={
    "user_id": 1, "qr_code": "PT-A03", "waste_type": "快递纸箱",
    "category": "快递纸箱", "grade": "完好", "score": 0.9,
    "photo": "/uploads/far.png", "photo_hash": "xyz999",
    "item_count": 1, "user_lat": 40.0, "user_lng": 116.0,
})
check("GPS far rejected", r10.status_code == 400)

# Admin bypass
admin = db.query(User).filter(User.role == "admin").first()
r12 = client.post("/api/submission", json={
    "user_id": admin.id, "qr_code": "PT-A03", "waste_type": "快递纸箱",
    "category": "快递纸箱", "grade": "完好", "score": 0.9,
    "photo": "/uploads/admin.png", "photo_hash": "adm001",
    "item_count": 1, "user_lat": 0, "user_lng": 0,
})
check("admin bypasses GPS", r12.status_code == 200)

# Food waste no image similarity check
r13 = client.post("/api/submission/pending", json={
    "user_id": 1, "waste_type": "外卖厨余",
    "category": "外卖厨余", "score": 0.8,
    "photo": "/uploads/test.png", "photo_hash": "abc123",
    "item_count": 1,
})
check("food waste no dupe check", r13.status_code == 200)

print()
print("=" * 60)
if errors:
    print(f"FAILED: {len(errors)} tests")
    for e in errors:
        print(f"  - {e}")
else:
    print("ALL TESTS PASSED")
print("=" * 60)

db.close()
sys.exit(1 if errors else 0)
