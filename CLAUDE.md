# 校园低碳回收全路径追踪系统 (LC_project)

## 项目定位
面向校园场景的低碳回收闭环 Demo，核心链路：扫码 → AI识别 → 归入批次 → 去向端认领 → 上传成品 → 反馈至投递用户。

## 技术栈
- 后端：Python FastAPI + SQLAlchemy + SQLite
- 前端：原生 HTML/CSS/JS 单页应用（SPA），底栏 Tab 切换三个视图
- AI：PyTorch MobileNetV3 Small（ImageNet 预训练权重）+ 类别索引映射 + 图像统计启发式规则，支持 mock 降级

## 当前开发阶段
- ✅ 核心闭环已跑通（7张表、16个API接口、前端SPA）
- ✅ README.md 和设计文档已更新，与代码一致
- ✅ 反作弊系统：GPS定位校验 + 30s冷却 + 图片相似度去重 + 多物品计数
- ✅ 登录重复显示Bug修复
- ❌ 尚未初始化 Git 仓库
- ❌ 缺少正式技术文档、PPT、测试

## 下一步计划
1. Git 初始化 + 推送到 GitLab/GitHub
2. 撰写正式技术文档（架构图、接口文档、数据库设计）
3. 制作答辩 PPT（用户场景先行 → 技术实现）
4. 准备演示视频素材
5. 补充异常处理与边界情况

## 项目路径
- 代码：`C:\Users\chenm\Desktop\program\LC_project`
- 设计文档：`C:\Users\chenm\Desktop\校园低碳回收追踪系统-项目设计文档.docx`
- 开发日志：`C:\Users\chenm\Desktop\program\LC_project\DEVLOG.md`（记录选题→设计→AI辅助→问题→迭代全过程，用于制作PPT）
- 启动：`python run.py`，访问 http://127.0.0.1:8000/
