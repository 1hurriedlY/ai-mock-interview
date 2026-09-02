/* 浏览器语音封装：ASR（语音识别）+ TTS（语音合成），基于 Web Speech API。
 *
 * - ASR：SpeechRecognition（zh-CN，interimResults）。一次一轮：点🎤开始聆听，
 *   识别文本实时回调 onInterim；用户停顿(浏览器静音检测)自动结束 → onResult(全文)；
 *   用户主动 stopListen → onDraft(保留文本供编辑，不自动发送)；出错 → onError。
 * - TTS：speechSynthesis，自动挑选中文语音，长文本按标点切句逐句朗读（避免
 *   浏览器长文本截断），新朗读自动打断上一句；speak/cancelSpeak 手动控制。
 * - 任一能力缺失 supported=false，调用方据此降级（隐藏按钮 / 提示走文字）。
 *
 * 模块级单例：多次调用返回同一组 ref，InterviewView 与 VoiceControl 状态共享。
 */
import { ref } from 'vue'

let singleton = null

export function useVoice() {
  if (!singleton) singleton = createVoice()
  return singleton
}

function createVoice() {
  const listening = ref(false)   // 正在聆听
  const speaking = ref(false)    // 正在朗读
  const autoSpeak = ref(false)   // AI 回复后是否自动朗读
  const asrSupported = ref(false)
  const ttsSupported = ref(false)

  let recognition = null
  let interimCb = null   // 识别中间文本（边说边看）
  let resultCb = null    // 自然结束：识别完整句
  let draftCb = null     // 手动停止：文本保留待发送
  let errorCb = null
  let speechSynth = null

  // ---------- 初始化：能力探测 + 中文语音加载 ----------
  if (typeof window !== 'undefined') {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SR) {
      asrSupported.value = true
      try {
        recognition = new SR()
        recognition.lang = 'zh-CN'
        recognition.interimResults = true
        recognition.continuous = false   // 单轮：停顿即结束，适合面试一问一答
        recognition.maxAlternatives = 1
      } catch {
        recognition = null
        asrSupported.value = false
      }
    }

    speechSynth = window.speechSynthesis || null
    ttsSupported.value = Boolean(speechSynth)
    if (speechSynth) {
      // getVoices 在部分浏览器异步填充，首次可能为空，监听 voiceschanged 补一次
      const prime = () => { speechSynth.getVoices() }
      try { speechSynth.addEventListener('voiceschanged', prime) }
      catch { speechSynth.onvoiceschanged = prime }
      prime()
    }
  }

  // ---------- ASR ----------
  function startListen() {
    if (!recognition || listening.value) return false
    interimCb && interimCb('')
    recognition.onresult = (ev) => {
      let interim = ''
      let finalAppend = ''
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i]
        if (res.isFinal) finalAppend += res[0].transcript
        else interim += res[0].transcript
      }
      const text = (finalAppend + interim).trim()
      if (finalAppend) recognition._lastFinal = (recognition._lastFinal || '') + finalAppend
      interimCb && interimCb(text || '')
    }

    recognition.onerror = (ev) => {
      recognition._error = ev.error
      // no-speech 静音超时：不算错误，按自然结束处理（无文本则不发送）
      if (ev.error && ev.error !== 'no-speech' && ev.error !== 'aborted') {
        errorCb && errorCb(voiceErrorText(ev.error))
      }
    }

    recognition.onend = () => {
      if (!listening.value) return
      listening.value = false
      const err = recognition._error
      recognition._error = null
      const full = (recognition._lastFinal || '').trim()
      recognition._lastFinal = ''

      if (recognition._manualStop) {
        // 用户主动停：全文保留给调用方（编辑后手动发送），不自动发送
        recognition._manualStop = false
        draftCb && draftCb(full)
      } else if (err === 'no-speech') {
        draftCb && draftCb('') // 没说话：静默清空
      } else if (full) {
        resultCb && resultCb(full) // 说完整句：自动发送
      } else {
        draftCb && draftCb('')
      }
    }

    recognition._lastFinal = ''
    recognition._error = null
    recognition._manualStop = false
    listening.value = true
    try {
      recognition.start()
    } catch {
      listening.value = false
      return false
    }
    return true
  }

  function stopListen() {
    if (recognition && listening.value) {
      recognition._manualStop = true
      try { recognition.stop() } catch { /* 忽略未启动时的 stop */ }
    }
  }

  // 注册本轮识别回调；返回 { stop } 便于组件内取用
  function listen({ onInterim, onResult, onDraft, onError } = {}) {
    interimCb = onInterim || null
    resultCb = onResult || null
    draftCb = onDraft || null
    errorCb = onError || null
    const started = startListen()
    return {
      started,
      stop: stopListen,
    }
  }

  // ---------- TTS ----------
  function zhVoice() {
    const vs = speechSynth ? speechSynth.getVoices() : []
    return (
      vs.find((v) => /^zh/i.test(v.lang) && /female|xiaoxiao|huihui|yaoyao|yunjian/i.test(v.name)) ||
      vs.find((v) => /^zh/i.test(v.lang)) ||
      null
    )
  }

  // 把文本按句子切成朗读队列（长文本逐句读，Chrome 整段读会中途静默）
  function splitSentences(text) {
    const parts = text.split(/(?<=[。！？!?；;\n])/)
    const out = []
    let buf = ''
    for (const p of parts) {
      const t = p.trim()
      if (!t) continue
      buf += t
      if (/[。！？!?；;]\s*$/.test(t) || buf.length >= 60) {
        out.push(buf)
        buf = ''
      }
    }
    if (buf.trim()) out.push(buf)
    return out.length ? out : [text.trim()]
  }

  let speakGen = 0 // 打断标记：新 speak / cancel 使旧队列失效
  function speak(text) {
    if (!speechSynth || !text) return
    const gen = ++speakGen
    speechSynth.cancel()
    const sentences = splitSentences(String(text))
    if (!sentences.length) return
    speaking.value = true

    const next = () => {
      if (gen !== speakGen) return // 已被打断，丢弃
      if (!sentences.length) {
        speaking.value = false
        return
      }
      const u = new SpeechSynthesisUtterance(sentences.shift())
      u.lang = 'zh-CN'
      const v = zhVoice()
      if (v) u.voice = v
      u.rate = 1.0
      u.pitch = 1.0
      u.onend = next
      u.onerror = next // 单句失败不阻塞后续
      speechSynth.speak(u)
    }
    next()
  }

  function cancelSpeak() {
    speakGen++
    speaking.value = false
    if (speechSynth) speechSynth.cancel()
  }

  function toggleAutoSpeak() {
    autoSpeak.value = !autoSpeak.value
    if (!autoSpeak.value) cancelSpeak()
  }

  return {
    listening,
    speaking,
    autoSpeak,
    asrSupported,
    ttsSupported,
    listen,
    stopListen,
    speak,
    cancelSpeak,
    toggleAutoSpeak,
  }
}

function voiceErrorText(code) {
  const map = {
    'not-allowed': '麦克风权限被拒绝，请允许后重试',
    'service-not-allowed': '语音服务不可用',
    'audio-capture': '未检测到麦克风设备',
    network: '语音识别网络异常',
    'language-not-supported': '当前浏览器不支持中文识别',
  }
  return map[code] || `语音识别失败（${code}）`
}
