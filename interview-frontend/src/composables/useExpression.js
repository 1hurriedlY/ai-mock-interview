/* 摄像头表情识别封装：加载 face-api 模型 → 打开摄像头 → 周期采样表情 → 输出实时标签 + 时间轴。
 *
 * 视觉识别全在本地浏览器完成（TinyFaceDetector + FaceExpressionNet），不上传画面；
 * 只有「表情时间轴」(采样序列) 在面试结束时随 /end 上传给评分 Agent 做表情点评。
 *
 * 表情标签池（FaceExpressionNet 输出）：
 *   neutral(中性) happy(开心) sad(难过) angry(生气) fearful(害怕)
 *   disgusted(厌恶) surprised(惊讶)
 *
 * 用法：
 *   const expr = useExpression()
 *   await expr.init()               // 加载模型 + 请求摄像头；返回 boolean
 *   expr.start()                    // 开始每 2s 采样
 *   expr.current.value              // 最近一次识别标签（'未检测到人脸' 等由上层提示）
 *   expr.sequence.value             // 时间轴 [{time, expression, confidence}]
 *   expr.stop()                     // 停止采样；保留序列供 /end 上传
 *   expr.closeCamera()              // 关闭摄像头（离开页面/结束面试时释放）
 *   expr.reset()                    // 新一场面试清零序列
 *
 * 安全：所有 camera.onerror / loadModels 失败均有降级——摄像头不可用时
 *   init() 返回 false，调用方静默隐藏摄像头区，面试照常进行（视觉是加分项）。
 */
import { ref } from 'vue'

// 模型放在 vite public/models，浏览器 /models/tiny_face_detector_model-*.bin
const MODEL_DIR = '/models'
const SAMPLE_INTERVAL_MS = 2000 // 每 2 秒采样一次
const EXPRESSION_CN = {
  neutral: '平静',
  happy: '开心',
  sad: '难过',
  angry: '生气',
  fearful: '紧张',
  disgusted: '厌恶',
  surprised: '惊讶',
}
const CONFETTI_KEYS = new Set(['happy', 'surprised'])

let singleton = null

export function useExpression() {
  if (!singleton) singleton = createExpression()
  return singleton
}

async function loadFaceApi() {
  // 动态 import：摄像头未授权/浏览器不支持 getUserMedia 时不拖累首屏
  const m = await import('@vladmandic/face-api')
  const faceapi = m.default || m
  if (!faceapi.nets) {
    // 该 fork 命名空间带 nets；极端情况返回包装
    return {
      nets: {
        tinyFaceDetector: faceapi.nets?.tinyFaceDetector || null,
        faceExpressionNet: faceapi.nets?.faceExpressionNet || null,
      },
      ...faceapi,
    }
  }
  return faceapi
}

function createExpression() {
  const cameraReady = ref(false) // 摄像头流已打开
  const modelReady = ref(false)  // 模型已加载
  const started = ref(false)     // 正在采样
  const current = ref('')        // 当前表情（中文标签）
  const happy = ref(false)       // 当前是否开心/惊讶（前端撒花用）
  const lastDetectedAt = ref(0)  // 上次识别到人脸的时间戳
  const sequence = ref([])       // 时间轴 [{ time, expression, confidence }]
  const error = ref('')          // 最近一次错误提示（摄像头权限/无人脸等）

  let faceapi = null
  let stream = null
  let video = null
  let timer = null
  let startTs = 0 // 本场面试开始时间戳（时间轴 time 基准）

  // ---------- 初始化：先加载模型，再开摄像头 ----------
  async function init() {
    // 已就绪直接返回
    if (stream && cameraReady.value && modelReady.value) return true
    try {
      faceapi = await loadFaceApi()
    } catch (e) {
      console.warn('[expr] face-api 动态加载失败', e)
      error.value = '表情模型加载失败，本次面试不启用表情分析'
      return false
    }
    if (!faceapi.nets?.tinyFaceDetector || !faceapi.nets?.faceExpressionNet) {
      error.value = '表情模型缺失（tinyFaceDetector/faceExpressionNet）'
      return false
    }

    try {
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_DIR)
      await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_DIR)
      modelReady.value = true
    } catch (e) {
      console.warn('[expr] 模型加载失败（network/file）', e)
      error.value = '表情模型文件加载失败，请刷新重试'
      return false
    }

    // 请求摄像头（本地 http://localhost 属于安全上下文，Chrome/Edge 可用）
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      })
      cameraReady.value = true
    } catch (e) {
      console.warn('[expr] 摄像头不可用', e?.name, e)
      if (e?.name === 'NotAllowedError') error.value = '摄像头权限被拒绝（表情分析不启用，可继续面试）'
      else if (e?.name === 'NotFoundError') error.value = '未检测到摄像头（表情分析不启用）'
      else error.value = '摄像头打开失败（表情分析不启用）'
      return false
    }
    return true
  }

  // 绑定 <video> 元素（摄像头预览由 CameraPreview 提供）
  function attachVideo(v) {
    video = v || null
    if (video && stream) video.srcObject = stream
  }

  // ---------- 采样 ----------
  function start() {
    if (started.value || !modelReady.value || !cameraReady.value || !video) return
    started.value = true
    startTs = Date.now()
    sequence.value = []
    lastDetectedAt.value = 0
    tick()
    timer = setInterval(tick, SAMPLE_INTERVAL_MS)
  }

  async function tick() {
    if (!started.value || !video || video.readyState < 2) return
    try {
      const det = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({
        inputSize: 320,
        scoreThreshold: 0.5,
      })).withFaceExpressions()
      if (!det) {
        // 没人脸：若之前有人脸且超过 3 秒，标记一次断点
        const now = Date.now()
        if (lastDetectedAt.value && now - lastDetectedAt.value > 3000) {
          sequence.value.push({ time: secs(now), expression: 'no_face', confidence: 0 })
          lastDetectedAt.value = 0 // 只记一次断点，避免连续灌
        }
        return
      }
      lastDetectedAt.value = Date.now()
      const exp = pickExpression(det.expressions)
      current.value = EXPRESSION_CN[exp] || exp
      happy.value = CONFETTI_KEYS.has(exp)
      sequence.value.push({
        time: Math.round(secs(Date.now())),
        expression: exp,
        confidence: Math.round((det.expressions[exp] || 0) * 100) / 100,
      })
    } catch (e) {
      // 单帧失败不致命（模型推理偶发），继续下一帧
      console.debug('[expr] 采样失败', e)
    }
  }

  function secs(ts) {
    return (ts - startTs) / 1000
  }

  function pickExpression(exps) {
    // 取置信度最高；happy/surprised 略加分（面试微笑正向）不在此处理
    let best = 'neutral'
    let bestScore = -1
    for (const [k, v] of Object.entries(exps)) {
      if (v > bestScore) { best = k; bestScore = v }
    }
    return best
  }

  // ---------- 停止 / 清理 ----------
  function stop() {
    started.value = false
    if (timer) { clearInterval(timer); timer = null }
  }

  // 关闭摄像头（释放设备灯与权限），保留 sequence 供上传
  function closeCamera() {
    stop()
    if (video) { video.srcObject = null }
    if (stream) { stream.getTracks().forEach((t) => t.stop()) }
    stream = null
    cameraReady.value = false
    video = null
  }

  // 新一场面试：序列清零（current 清空，摄像头默认关闭等新场 init）
  function reset() {
    sequence.value = []
    current.value = ''
    happy.value = false
    lastDetectedAt.value = 0
    error.value = ''
  }

  // 结束面试 / 离开页面时调用（组件负责兜底）
  function dispose() {
    closeCamera()
  }

  return {
    cameraReady,
    modelReady,
    started,
    current,
    happy,
    sequence,
    error,
    init,
    attachVideo,
    start,
    stop,
    closeCamera,
    reset,
    dispose,
  }
}
