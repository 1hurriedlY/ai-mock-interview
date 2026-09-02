# 模拟面试 AI 助手（前端）

Vue3 + Vite 前端，调用后端 `http://localhost:8000` 的 `/api` 接口（vite 代理）。

## 开发

```bash
npm install        # 首次安装依赖
npm run dev        # 启动开发服务器（端口 5173，/api 代理到 8000）
```

## 构建

```bash
npm run build      # 产物输出到 dist/
npm run preview    # 本地预览构建产物
```

## 目录

- `src/views/` — 页面：Login / Home（开始面试）/ Interview（流式对话+语音+表情）/ Report（评分报告）/ History / Industry / Project
- `src/components/` — ScoreRadar / ExpressionChart / CameraPreview / VoiceControl
- `src/composables/` — useVoice（Web Speech 封装）、useExpression（face-api 表情识别封装，动态 import 懒加载）
- `src/api/index.js` — axios 封装（自动带 JWT token）
- `public/models/` — face-api.js 表情识别模型（TinyFaceDetector + FaceExpressionNet），需随构建产物部署

## 依赖

- vue 3、vue-router 5、axios、echarts 6、@vladmandic/face-api 1.7（face-api.js 维护版 fork）
- 开发：vite、@vitejs/plugin-vue
