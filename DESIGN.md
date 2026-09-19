---
name: 一生一案学业发展管理系统
description: 清晰、可信的校园学业协作工作台
colors:
  primary: "#2878f5"
  primary-hover: "#1762d4"
  primary-soft: "#eaf3ff"
  app-background: "#f4f7fb"
  surface: "#ffffff"
  surface-soft: "#f8fafd"
  ink: "#172033"
  ink-secondary: "#445269"
  ink-muted: "#6e7c91"
  line: "#e5eaf2"
  success: "#129466"
  warning: "#d97706"
typography:
  headline:
    fontFamily: "PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.35
  title:
    fontFamily: "PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    height: "40px"
    padding: "0 18px"
  nav-active:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    height: "44px"
    padding: "0 14px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px"
---

# Design System: 一生一案学业发展管理系统

## Overview

**Creative North Star: “清晰的校园工作台”**

视觉系统以白色工作区、浅灰页面背景和克制的亮蓝色强调构成。它承载高频的校园管理任务，因此使用熟悉的侧栏、顶部栏、表格和表单结构，让用户把注意力放在学生、班级、任务与数据上。

界面拒绝渐变、玻璃拟态、霓虹色、夸张阴影、过大的圆角和装饰性动效。不同角色可以有语义差异，但导航与交互规则保持一致。

**Key Characteristics:**

- 白色侧栏和顶部栏形成稳定框架。
- 蓝色只强调主要动作、当前导航和关键链接。
- 数据面板用边界和轻微层次分组，不依赖厚重阴影。
- 表格、筛选与状态标签优先保证扫读效率。

## Colors

主色是清晰的工作台蓝，配合偏冷的浅灰背景与中性深色文字。

### Primary

- **工作台蓝** (#2878F5)：主要按钮、活动导航、链接与键盘焦点。
- **深蓝交互** (#1762D4)：悬停和按下状态。
- **浅蓝选中** (#EAF3FF)：导航选中、轻量信息状态和选中行。

### Neutral

- **页面雾灰** (#F4F7FB)：应用内容区背景。
- **纯白表面** (#FFFFFF)：侧栏、顶部栏、表格和主要面板。
- **主文字** (#172033)：标题与关键数据。
- **次文字** (#445269)：正文与表格内容。
- **弱文字** (#6E7C91)：说明与辅助信息。
- **分隔线** (#E5EAF2)：边框、表格分隔和布局边界。

**The One Blue Rule.** 蓝色只用于操作与状态，不作为无意义装饰。

## Typography

**Display Font:** PingFang SC, Microsoft YaHei, system-ui, sans-serif
**Body Font:** PingFang SC, Microsoft YaHei, system-ui, sans-serif

**Character:** 单一无衬线字体保证中英文混排稳定，数字采用等宽数字特性提升看板和表格的对齐感。

### Hierarchy

- **Headline** (600, 20px, 1.35)：页面标题。
- **Title** (600, 16px, 1.4)：面板和模块标题。
- **Body** (400, 14px, 1.6)：正文、表格与表单内容，说明文字最长控制在 75ch。
- **Label** (600, 12px, 1.4)：字段、筛选条件和状态说明。

## Elevation

系统以边框和背景层级区分区域。顶部栏允许一层低强度环境阴影，普通面板保持平面；下拉层、弹窗和悬浮交互才使用更高层阴影。

### Shadow Vocabulary

- **顶部栏** (`0 2px 10px rgba(23, 32, 51, 0.06)`): 固定框架和滚动内容之间的轻微分离。
- **悬浮层** (`0 8px 24px rgba(23, 32, 51, 0.10)`): 下拉菜单、弹窗和需要离开页面平面的临时层。

**The Flat-by-Default Rule.** 静态内容面板默认不使用宽而模糊的阴影。

## Components

### Buttons

- **Shape:** 6–8px 圆角，主要按钮高度 40px。
- **Primary:** 工作台蓝底、白字，水平内边距 18px。
- **Hover / Focus:** 悬停转深蓝；键盘焦点使用 2px 蓝色轮廓。
- **Secondary / Ghost:** 白底或透明底，以细边框和文字色表达层级。

### Chips

- **Style:** 6px 圆角或状态胶囊，仅用于短标签。
- **State:** 选中使用浅蓝底与主蓝文字；成功、警告和错误使用各自语义色。

### Cards / Containers

- **Corner Style:** 6–8px。
- **Background:** 白色主表面或极浅灰辅助表面。
- **Shadow Strategy:** 默认无阴影，依靠边框与背景分层。
- **Border:** 1px 分隔线色。
- **Internal Padding:** 16–24px。

### Inputs / Fields

- **Style:** 白色背景、1px 中性边框、8px 圆角。
- **Focus:** 主蓝描边与清晰焦点环。
- **Error / Disabled:** 错误显示语义红与文本说明；禁用态降低对比但保持可读。

### Navigation

桌面使用白色侧栏与白色顶部栏。导航项默认使用次文字色，悬停显示浅灰蓝底，当前项使用浅蓝底和主蓝文字。窄屏保留图标并隐藏长文本。

## Do's and Don'ts

### Do:

- **Do** 使用 #2878F5 表示主要操作、当前导航和关键链接。
- **Do** 用 #F4F7FB 页面背景与白色表面建立层级。
- **Do** 为表格行、按钮、输入框和导航提供完整的悬停、焦点与禁用状态。
- **Do** 让状态同时具备颜色、文字或图标信息。

### Don't:

- **Don't** 使用渐变、玻璃拟态、霓虹色、夸张阴影或装饰性动效。
- **Don't** 使用大面积深色侧栏压迫内容。
- **Don't** 给普通卡片使用超过 16px 的圆角。
- **Don't** 把每个信息块都包装成悬浮卡片。
- **Don't** 用超过 1px 的彩色侧边条作为卡片强调。

## 全站排版约束

所有角色共用 style.css 中的字体、页面标题和标题字重变量。普通页面标题为 20px/600，档案姓名为 24px（窄屏 22px），正文基准 14px/400；统计数字可保留 24–30px。中文使用正常字间距，导航只强调选中项。常规面板使用 6–8px 圆角和细边框，不添加装饰渐变或阴影；图表网格和悬浮交互层保留其功能性样式。
