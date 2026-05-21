# Assets（静态资源）文档

> 本目录包含会被 webpack/Vite 处理和复制的静态资源文件。

---

## 目录结构

```
assets/
├── README.md              # 本文档
│
└── styles/
    └── global.css        # 全局样式
```

---

## styles/global.css - 全局样式

### 内容说明

#### 基础重置
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
```

#### 全局字体
```css
html, body, #app {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}
```

#### 涨跌颜色类
```css
.text-rise   { color: #f56c6c; }  /* 红色 - 涨 */
.text-fall   { color: #67c23a; }  /* 绿色 - 跌 */
.text-flat   { color: #909399; }  /* 灰色 - 平 */
```

#### 页面布局类
```css
.page-container { padding: 16px; }           /* 页面容器 */
.page-title { font-size: 20px; font-weight: 600; margin-bottom: 16px; } /* 页面标题 */
.card-header { font-size: 16px; font-weight: 600; margin-bottom: 12px; } /* 卡片标题 */
.empty-state { text-align: center; padding: 40px 0; color: #909399; } /* 空状态 */
```

#### 统计数字类
```css
.stat-value { font-size: 24px; font-weight: 600; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
```

---

## 引入方式

在 `main.ts` 中引入：
```typescript
import './assets/styles/global.css'
```

---

## 后续扩展

- 添加自定义 CSS 变量（主题色）
- 添加响应式工具类
- 引入 Element Plus 主题定制
