# 校园低碳回收全路径追踪系统 (LC_project)

> 基于 AI 识别与批次化管理的回收闭环 Demo

## 一、项目简介

面向校园场景，构建一套以 AI 视觉识别为核心、以「点位 + 日期 + 品类」批次化管理为骨架的回收物全路径追踪系统。

**核心闭环**：
扫点位码 → AI 识别投递 → 归入批次 → 去向端认领 → 上传成品照片 → 反馈至原投递用户。

## 二、目录结构

```
LC_project/
├── requirements.txt
├── run.py                   # 一键启动
└── src/
    ├── config.py            # 配置
    ├── main.py              # FastAPI 入口
    ├── database.py          # 数据库连接
    ├── models.py            # 7 张 ORM 表
    ├── schemas.py           # Pydantic
    ├── seed.py              # 初始化种子数据
    ├── api/                 # 6 组 REST 接口（扫码/AI/投递/批次/用户/排行）
    ├── services/            # 业务逻辑（AI / 批次 / 碳因子 / 通知）
    └── web/                 # 前端（原生 HTML/CSS/JS 单页应用，含投递/去向/排行三 Tab）
```

## 三、快速启动

```bash
# 1. 安装依赖（torch 体积较大，可换国内源）
pip install -r requirements.txt

# 2. 一键启动（自动初始化数据库 + 种子数据）
python run.py
```

启动后访问：
- 系统首页（单页应用，含投递/去向/排行三个 Tab）: http://127.0.0.1:8000/
- API 文档（Swagger）: http://127.0.0.1:8000/docs

> 前端为原生 HTML/CSS/JS 单页应用（SPA），通过底栏 Tab 切换角色视图，无需跳转不同页面。

## 四、Demo 演示流程

1. 打开首页，扫码（或选择）回收点 → 自动记录点位与时间
2. 拍照上传回收物 → AI 识别品类与完整度 → 自动归入批次
3. 切换到「去向端」→ 认领某批次 → 上传成品照片
4. 回到用户端「我的纸箱」→ 看到批次故事与成品反馈
5. 查看排行榜 → 累计减碳量

## 五、AI 说明

- 使用 torchvision 预训练 MobileNetV3 Small（ImageNet 权重）提取特征，通过 ImageNet 类别索引映射聚合到"纸箱/塑料/玻璃"三品类，结合图像统计启发式规则（边缘密度、亮度方差）评估完整度（完好/轻损/破损/受潮）
- 未在回收物数据集上微调——Demo 阶段采用"预训练特征 + 类别映射 + 启发式规则"的工程折中方案，后续可采集真实数据微调提升准确率
- 无 GPU 也可 CPU 运行
- 若未安装 torch，自动降级为 mock 模式（按 RGB 通道统计特征模拟输出），保证 Demo 可演示

## 六、数据库

SQLite，文件位于 `lc_project.db`，启动时自动创建 7 张表并写入种子数据：
- users / points / batches / submissions / reuse_items / notifications / carbon_factors
