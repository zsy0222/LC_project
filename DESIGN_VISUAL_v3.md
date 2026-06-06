# LC_project · frontend-design v3 最终版

> 基于 `frontend-design` skill · Tone: Organic/Tactile/手帐本
> 所有图标已用 Agnes API 生成完毕，存放于 `/checkin/`

---

## 一、已完成的素材库（35 张图）

```
/checkin/
├── bg_login.png          # 登录背景：水彩校园风景
├── logo_tree.png         # Logo：树形回收符号
│
├── cat_food.png          # 🍚→外卖厨余  米饭+筷子
├── cat_paper.png         # 📦→快递纸箱  纸箱+♻
├── cat_plastic.png       # 🥡→塑料      水瓶
├── cat_hazard.png        # 🔋→有害      电池+灯泡
│
├── nav_delivery.png      # 投递 tab    手持枝条
├── nav_reuser.png        # 去向 tab    手推车+苗
├── nav_reward.png        # 成果 tab    麻绳礼盒+叶
├── nav_shop.png          # 兑换 tab    小摊位+盆栽
├── nav_rank.png          # 排行 tab    三株高矮苗
│
├── icon_camera.png       # 拍照图标    复古双反相机
├── icon_pin.png          # 定位图标    木牌+土堆+芽
├── icon_confirm.png      # 确认勾      藤蔓弯成勾
│
├── track_submit.png      # 追踪-投递   手放编织篮
├── track_batch.png       # 追踪-归入   木箱聚集
├── track_claimed.png     # 追踪-认领   双手交换苗
├── track_product.png     # 追踪-成品   手工纸盒+蝴蝶结
│
├── badge_seed.png        # 🌰 种子    橡果+土堆
├── badge_sprout.png      # 🌱 发芽    破土双叶苗
├── badge_sapling.png     # 🌿 树苗    掌高小树
├── badge_smalltree.png   # 🪴 小树    圆冠成树
├── badge_bigtree.png     # 🌳 大树    参天大树
│
├── empty_delivery.png    # 空-投递    回收箱+落叶
├── empty_order.png       # 空-抢单    空货架+蛛网
├── empty_gallery.png     # 空-橱窗    画框+调色板
│
├── s01~s12               # 商城商品 12张
└── tree_stage_01~20      # 20阶段树木生长
```

---

## 二、字体系统

| 角色 | 字体 | 说明 |
|---|---|---|
| 登录艺术标题 | `Georgia, serif` italic | "Low Carbon" 英文刊头 |
| 登录中文副标 | `'KaiTi', serif` | 楷体手写感 |
| 页面标题 H2 | `'PingFang SC', sans-serif` | 系统黑体 |
| 数字/碳积分 | `Georgia, serif` | 衬线数字有记录感 |
| 正文 | `'PingFang SC', 'Microsoft YaHei'` | 保持稳定可读 |

---

## 三、大地色板

```
--soil:      #4E342E   深咖啡    主要文字
--bark:      #6D4C41   树皮棕    分割线/边框
--moss:      #33691E   苔藿深绿  主按钮
--lichen:    #8BC34A   地衣嫩绿  悬停/高亮
--parchment: #FFF8E1   羊皮纸黄  卡片底色
--clay:      #EFEBE9   陶土灰    页面底色
--soil-red:  #BF360C   红土色    有害/警告
```

**品类材质色**：

| 品类 | 主色 | 卡片底 | "材质" |
|---|---|---|---|
| 外卖厨余 | #E65100 | #FFF3E0 | 温暖陶土 |
| 快递纸箱 | #5D4037 | #EFEBE9 | 稳重牛皮纸 |
| 塑料 | #1565C0 | #E3F2FD | 清透水面 |
| 有害 | #BF360C | #FBE9E7 | 警示红土 |
| 碳积分 | #33691E | #F1F8E9 | 自然苔藓 |
| 兑换 | #4A148C | #F3E5F5 | 稀有紫晶 |

---

## 四、登录页 — 全屏沉浸

### 现状
已实现：全屏视差风景 + "Low Carbon" 艺术字 + 浮窗登录

### 图标替换
- `logo_tree.png` 替换顶部 🌱 emoji，放置在艺术字上方
- "拖动探索" 提示改为画面角落的小石头，hover 才显示文字

### 登录浮窗
- 底色 → `--parchment`
- 加 CSS 横线纸纹理（`repeating-linear-gradient` 22px 间距）
- 浮窗不出现在页面加载时——用户点击风景任意处才淡入
- 点击处波纹扩散动画（CSS `@keyframes ripple`）

---

## 五、底栏 — 浮动胶囊

5 个 tab 图标全部换成手绘：

| Tab | 新图标 | 文件 |
|---|---|---|
| 📸 投递 | 手持枝条 | `nav_delivery.png` |
| 📦 去向 | 手推车+苗 | `nav_reuser.png` |
| 🎁 成果 | 麻绳礼盒+叶 | `nav_reward.png` |
| 🏪 兑换 | 小摊位+盆栽 | `nav_shop.png` |
| 🏆 排行 | 三株高矮苗 | `nav_rank.png` |

底栏样式改为浮动胶囊：
- `border-radius: 28px`，左右各 16px margin
- 底部 8px 距离 → 浮起效果
- 下方更重的 `box-shadow`
- 选中 tab：细苔藓绿下划线（2px × 16px），不全胶囊背景

---

## 六、品类选择 — 扇形扑克牌

### 图标
- 四张卡片用已有的 `cat_food/png` 等品类插画，替换 emoji
- 卡片底色为品类专属材质色

### 动画
- 初始：四卡微旋转（-3°/-1°/1°/3°），像扇形展开
- 选中：该卡归正（rotate 0），其他三张缩到 0.92 + opacity 0.5
- 纯 CSS `transition`，200ms

---

## 七、拍照区 — 手工相纸

### 图标替换
- 拍照区占位图换为 `icon_camera.png`
- 定位标记换为 `icon_pin.png`
- 确认勾换为 `icon_confirm.png`（藤蔓弯勾）

### 样式
- 上传框 → `border-radius: 20px 6px 20px 6px`（手工裁剪相纸）
- 拍照后图片加暗角（`radial-gradient` 叠加）
- AI 识别中 → 三个手写文字标签，依次出现（打字机延迟）

---

## 八、成果页 — 手帐风格

### 图标替换
- 碳积分阶段用 `badge_seed~bigtree` 5 张替换原有 emoji
- 追踪步骤用 `track_submit~product` 4 张

### 树木区
- 树图加大到占卡片 60%
- 下方用同心圆 CSS 模拟"年轮"，投递一次加一圈

### 追踪
- 连接线改为虚线（`border: 2px dashed`）
- 当前节点：描边动画（`stroke-dasharray` 配合 `animation`）

### 成品橱窗
- 照片不规则边框 + 轻微旋转（`rotate(-1deg)~2deg`）
- 像手帐贴纸

---

## 九、兑换商城

- 已有 12 张商品图（不需要额外生图）
- 兑换弹窗按钮改为"凸起印章"风格

---

## 十、空状态

三段空状态用已有图：
- 暂无投递 → `empty_delivery.png`（回收箱+落叶）
- 暂无可抢 → `empty_order.png`（空货架+蛛网）
- 暂无成品 → `empty_gallery.png`（画框+调色板）

不做骨架屏/闪烁。数据到了直接淡入替换。

---

## 十一、按钮触感

```css
.btn-primary {
  background: var(--moss);
  border-bottom: 3px solid #1B5E20;  /* 底部厚度 */
}
.btn-primary:active {
  border-bottom-width: 1px;
  transform: translateY(2px);          /* 按压下沉 */
}
```

## 十二、动效清单（10 个）

| 动效 | 时机 | 时长 |
|---|---|---|
| 视差拖拽 | 登录页拖动风景 | 实时 |
| 松手弹回 | 释放拖动 | 800ms |
| 浮窗淡入 | 点击风景 | 800ms |
| 品类选中归正 | 翻牌选中 | 200ms |
| 其他卡片退后 | 翻牌未选中 | 200ms |
| 拍照暗角 | 图片加载 | 400ms |
| 识别标签贴入 | AI 结果 | 80ms/个 |
| 按钮按压下沉 | 点击按钮 | 100ms |
| 树木交叉淡入 | 阶段切换 | 300ms |
| 弹窗淡入 | 打开弹窗 | 200ms |

---

## 十三、实施分三批

**P0 第一批**（色板+字体+按钮+底栏）：CSS ~90 行
**P1 第二批**（品类卡片+拍照区+图标替换）：CSS ~80 行 + HTML 图标 src 替换
**P2 第三批**（年轮环+追踪虚线+弹窗纹理+空状态图）：CSS ~70 行 + 少量 JS

**总计：CSS ~240 行 + HTML 图标约 20 处替换**
