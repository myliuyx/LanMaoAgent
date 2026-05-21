# Components（组件）文档

> 本目录包含所有 Vue 组件，分为三层：
> - **通用基础组件**（`base/`）— 纯 UI 组件，可复用
> - **业务组件**（各子目录）— 面向业务，复用范围有限
> - **页面组件**（`pages/`）— 路由页面

---

## 目录结构

```
components/
├── README.md              # 本文档
│
├── base/                  # 通用基础组件
│   ├── BaseChart.vue      # ECharts 统一封装 ✅
│   ├── BaseStatCard.vue   # 统计卡片
│   ├── BaseDrawer.vue     # 抽屉封装
│   ├── BaseDatePicker.vue # 日期选择器封装
│   ├── BaseTag.vue        # 标签封装
│   ├── BaseEmpty.vue      # 空状态组件
│   └── VirtualTable.vue   # 虚拟滚动表格
│
├── dashboard/             # Dashboard 业务组件（待实现）
│   ├── DataOverviewCard.vue
│   ├── TodayJobStatus.vue
│   └── FailedJobAlert.vue
│
├── selection/             # 选股模块业务组件
│   ├── FilterPanel.vue   # 选股筛选面板 ✅
│   ├── ResultTable.vue
│   └── TemplateSaveDialog.vue
│
├── stock/                 # 个股模块业务组件（待实现）
│   ├── KLineChart.vue    # K线图（lightweight-charts）✅
│   ├── VolumeChart.vue   # 成交量图表（ECharts）✅
│   ├── FactorTable.vue
│   └── FinanceTable.vue
│
├── board/                 # 板块模块业务组件（待实现）
│   ├── BoardList.vue
│   └── MemberTable.vue
│
└── job/                   # 任务模块业务组件（待实现）
    ├── JobTable.vue
    ├── JobDetailDrawer.vue
    └── JobLogViewer.vue
```

---

## 当前状态

所有组件文件**已创建目录结构**，但**尚未实现具体代码**。
目前页面直接使用 Element Plus 原生组件，后续逐步抽取为可复用组件。

---

## base/ - 通用基础组件（待实现）

### VirtualTable.vue - 虚拟滚动表格
- **用途**：超过 500 条数据时使用，避免页面卡顿
- **依赖**：`vue-virtual-scroller`
- **Props**：`items`, `itemSize`, `keyField`
- **预计实现**：基于 `RecycleScroller` 封装

### BaseChart.vue - 图表封装
- **用途**：封装 ECharts 常用配置，减少重复代码
- **Props**：`option`, `height`, `width`
- **预计实现**：基于 `echarts.init` + `setOption` 封装

### BaseDatePicker.vue - 日期选择器封装
- **用途**：统一日期格式处理
- **Props**：`modelValue`, `type`（date/daterange）
- **预计实现**：封装 `el-date-picker`

### BaseStatCard.vue - 统计卡片
- **用途**：Dashboard 数据总览卡片
- **Props**：`title`, `value`, `prefix`, `suffix`
- **预计实现**：封装 `el-card` + `el-statistic`

### BaseDrawer.vue - 抽屉封装
- **用途**：统一抽屉尺寸和样式
- **Props**：`visible`, `title`, `size`
- **预计实现**：封装 `el-drawer`

### BaseTag.vue - 标签封装
- **用途**：统一状态标签样式
- **Props**：`type`, `status`
- **预计实现**：根据 `status` 自动映射 `type` 和 `label`

---

## dashboard/ - Dashboard 业务组件（待实现）

### DataOverviewCard.vue
- **用途**：Dashboard 首页数据总览卡片
- **预计包含**：股票总数、日线记录数、财务记录数、因子记录数

### TodayJobStatus.vue
- **用途**：今日任务状态概览
- **预计包含**：成功/失败任务数、运行中任务列表

### FailedJobAlert.vue
- **用途**：失败任务告警
- **预计包含**：失败任务列表、快速重跑入口

---

## selection/ - 选股模块业务组件（待实现）

### BaseChart.vue ✅
- **用途**：ECharts 统一封装（Phase 3.1.2 P1）
- **Props**：`options`（ECharts 选项对象）、`height`（默认300px）、`autoResize`
- **Exposes**：`setOption(opts, notMerge?)`、`resize()`、`getInstance()`
- **功能**：init/dispose/resize 全自动化，options 变化自动重绘，支持 Bar/Line/Candlestick
- **注意**：`options` 完全由父组件控制，可传入 computed 或 reactive 对象

### FilterPanel.vue ✅
- **用途**：选股筛选条件面板（Phase 3.2.3 P1）
- **Props**：`modelValue`（SelectionFilters）、`tradeDates`、`industries`、`loading`
- **Emits**：`update:modelValue`、`search`
- **功能**：交易日/行业下拉、排除ST、ROE/换手率/趋势评分输入、查询/重置
- **注意**：行业列表依赖 `GET /selection/industries` 接口（后端未完成时静默忽略）

### ResultTable.vue
- **用途**：选股结果表格
- **预计包含**：列配置、排序、分页、跳转个股详情

### TemplateSaveDialog.vue
- **用途**：保存选股模板弹窗
- **预计包含**：模板名称输入、筛选条件预览

---

## stock/ - 个股模块业务组件（待实现）

### KLineChart.vue ✅
- **用途**：K 线图（Phase 3.2.1 P0）
- **依赖**：`lightweight-charts`
- **Props**：
  - `data: KLineData[]` — K线数据，`KLineData` 包含 `trade_date / open / high / low / close / volume`
  - `showVolume: boolean` — 是否显示成交量（默认 true）
  - `showGrid: boolean` — 是否显示网格（默认 true）
  - `height: number` — 高度（默认 400）
- **Emits**：`click(data: KLineData)` — 点击 K 线触发
- **暴露方法**：`resetZoom()` — 重置缩放；`setData(data)` — 手动设置数据
- **功能**：日线 K 线、缩放、拖拽、成交量柱状图、十字光标

### VolumeChart.vue ✅
- **用途**：成交量柱状图（Phase 3.2.2 P1）
- **依赖**：`echarts`（按需引入）
- **Props**：
  - `data: StockDaily[]` — 行情数据
  - `height: number` — 高度（默认 200px）
  - `showMA: boolean` — 是否显示 MA5 均线（默认 true）
  - `upColor/downColor` — 涨跌颜色
- **Emits**：`click(data: StockDaily)`
- **暴露方法**：`setData()`、`syncCrosshair({ dataIndex })`（供外部同步十字光标）
- **功能**：成交量柱状图（红跌绿涨）、MA5 均线、Tooltip、缩放、响应式

### FactorTable.vue
- **用途**：技术因子表格
- **预计包含**：MA、RSI、MACD、ATR、趋势评分等

### FinanceTable.vue
- **用途**：财务指标表格
- **预计包含**：EPS、BPS、ROE、毛利率、净利率、营收同比等

---

## board/ - 板块模块业务组件（待实现）

### BoardList.vue
- **用途**：板块列表组件
- **预计包含**：搜索、类型筛选、排序

### MemberTable.vue
- **用途**：板块成分股表格
- **预计包含**：成分股列表、涨跌幅排序、跳转个股

---

## job/ - 任务模块业务组件（待实现）

### JobTable.vue
- **用途**：任务列表表格
- **预计包含**：状态筛选、分页、跳转详情

### JobDetailDrawer.vue
- **用途**：任务详情抽屉
- **预计包含**：任务详情、日志查看、重跑按钮

### JobLogViewer.vue
- **用途**：任务日志查看器
- **预计包含**：日志分页、关键词高亮
