# 校园低碳回收全路径追踪系统 · 运行手册

## 一、环境要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10+ / macOS / Linux |
| Python | 3.10+ |
| 内存 | ≥ 4 GB（PyTorch 首次加载约 500MB） |
| 磁盘 | ≥ 2 GB（含 torch 依赖） |

## 二、快速启动

```bash
# 1. 进入项目目录
cd LC_project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python run.py
```

启动后访问：
- **系统首页**：http://127.0.0.1:8000/
- **API 文档**：http://127.0.0.1:8000/docs

> 启动时自动创建数据库 + 种子数据（19 个用户 / 4 个点位 / 6 个活动 / 26 条碳因子），无需手动初始化。

## 三、依赖说明

```
fastapi>=0.100.0
uvicorn[standard]
sqlalchemy>=2.0
pydantic>=2.0
torch>=2.0          # AI 识别（大体积，可换国内镜像源）
torchvision>=0.15
Pillow>=10.0
python-multipart    # 文件上传
```

如果 PyTorch 安装失败或不方便安装，在 `src/config.py` 中设置 `AI_MOCK_MODE = True`，系统将使用随机结果模拟 AI 识别。

## 四、目录结构

```
LC_project/
├── run.py                  # 一键启动入口
├── requirements.txt        # Python 依赖
├── REPORT.md               # 项目报告
├── MANUAL.md               # 本文件
├── README.md               # 项目说明
├── CLAUDE.md               # AI 开发上下文
├── DEVLOG.md               # 开发日志
├── lc_project.db           # SQLite 数据库（自动生成）
├── uploads/                # 上传文件存储
├── image/                  # 静态图片资源
│   ├── tree/               #   20 阶段树木生长图
│   ├── welcome/            #   10 张欢迎弹窗插画
│   ├── shop/               #   12 件商城商品图
│   ├── checkin/            #   7 天打卡图
│   ├── login/              #   登录页素材
│   ├── icons/              #   27 枚界面图标
│   └── ...
└── src/
    ├── config.py           # 全局配置（含反作弊参数）
    ├── main.py             # FastAPI 入口 + 路由注册
    ├── database.py         # 数据库初始化 + 轻量迁移
    ├── models.py           # 10 张 ORM 数据表
    ├── schemas.py          # Pydantic 请求/响应模型
    ├── seed.py             # 种子数据
    ├── api/                # 8 组 API 路由
    │   ├── scan.py         #   扫码 (1 endpoint)
    │   ├── predict.py      #   AI 预测 (1 endpoint)
    │   ├── submission.py   #   投递提交 (4 endpoints)
    │   ├── batch.py        #   批次管理 (5 endpoints)
    │   ├── user.py         #   用户相关 (5 endpoints)
    │   ├── rank.py         #   排行榜 (2 endpoints)
    │   ├── reward.py       #   碳积分奖励 (5 endpoints)
    │   └── activity.py     #   活动广场 (4 endpoints)
    ├── services/           # 业务逻辑
    └── web/
        └── index.html      # 单页应用前端（~2300 行）
```

## 五、关键配置

### 5.1 演示模式

```python
# src/config.py
DEMO_MODE = True   # 跳过 GPS 定位校验（答辩演示推荐）
AI_MOCK_MODE = True  # 强制 mock AI（不装 PyTorch 时）
```

### 5.2 反作弊参数

```python
COOLDOWN_SECONDS = 30            # 同点位提交冷却
PHOTO_SIMILARITY_THRESHOLD = 0.15  # 图片去重阈值
LOCATION_MAX_DISTANCE_M = 100    # GPS 最大允许距离
```

### 5.3 端口

```python
HOST = "127.0.0.1"
PORT = 8000
```

## 六、API 速查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scan/{qr_code}` | 扫码返回点位信息 |
| POST | `/api/predict` | AI 识别（上传图片） |
| GET | `/api/submission/pending/{user_id}` | 待确认投递列表 |
| POST | `/api/submission` | 提交投递 |
| GET | `/api/batches` | 批次列表 |
| POST | `/api/batch/claim` | 去向端认领批次 |
| POST | `/api/batch/reuse` | 上传成品反馈 |
| GET | `/api/batch/{id}/story` | 批次故事时间线 |
| GET | `/api/activities?user_id=` | 活动广场列表 |
| POST | `/api/activities/{id}/join?user_id=` | 报名活动 |
| DELETE | `/api/activities/{id}/leave?user_id=` | 取消报名 |
| POST | `/api/activities/{id}/upload?user_id=&photo=&desc=` | 上传活动作品 |
| GET | `/api/rank` | 排行榜 |
| GET | `/api/gallery?user_id=` | 成品橱窗 |
| GET | `/api/user/{id}/reward-status` | 碳积分奖励进度 |
| GET | `/api/shop/items` | 商城商品列表 |
| POST | `/api/shop/buy` | 碳积分兑换 |

完整接口文档：http://127.0.0.1:8000/docs

## 七、Demo 演示流程

```
1. 打开 http://127.0.0.1:8000/ → 登录封面 → 选"小南"进入
2. 投递页 → 选回收点 → 拍照 → AI 识别 → 确认投递
3. 退出 → 选去向端用户"美术社"→ 去向页 → 认领批次 → 上传成品
4. 退出 → 选"小南"→ 查看批次故事时间轴 + 成品橱窗
5. 活动页 → 报名"废纸换花盆"→ 上传作品 → 碳积分+0.5kg
6. 成果页 → 查看碳积分树木生长 → 连续打卡
7. 排行榜 → 查看全服排名
```

## 八、常见问题

**Q: PyTorch 安装太慢？**
```bash
pip install torch torchvision -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: 启动报错 `address already in use`？**
```bash
# 端口被占用，杀掉旧进程
netstat -ano | findstr :8000    # 找到 PID
taskkill /f /pid <PID>          # 杀掉进程
python run.py                   # 重新启动
```

**Q: 数据库损坏或需重置？**
```bash
rm lc_project.db    # 删除数据库文件
python run.py       # 重启自动重建
```

**Q: AI 模型加载失败？**
设置 `src/config.py` 中 `AI_MOCK_MODE = True`，使用模拟识别。

**Q: 投递按钮灰色无法点击？**
1. 先选择一个回收点位（从下拉选择框）
2. Demo 模式会自动跳过 GPS 校验
3. 确保已拍照上传

**Q: 去向端看不到批次？**
去向端用户有路径权限限制，只能看到自己负责的处理方向。管理员可见全部。
