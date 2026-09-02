/* 面试 SSE 流式聊天：用原生 fetch 解析 text/event-stream（axios 不支持流）。
 *
 * 后端事件设计：
 *   event: message  data: {"delta": "…"}                  逐个字符增量
 *   event: done     data: {"reply","action","reference","stage","finished"}  收尾
 *
 * 返回 { onMessage, send }：
 *   onMessage(cb)  注册回调（delta/action/reference/stage/finished 逐段回调）
 *   send(msg)      发起一次流式请求
 */
import { ref } from 'vue'
import { authState } from '../store/auth'

export function useStreamChat(sessionId) {
  const streaming = ref(false)
  const error = ref('')
  let handlers = { delta: () => {}, done: () => {} }

  function onMessage(cb) {
    handlers = { ...handlers, ...cb }
  }

  async function send(message) {
    if (streaming.value) return
    streaming.value = true
    error.value = ''
    try {
      const res = await fetch(`/api/interview/${sessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authState.token}`,
        },
        body: JSON.stringify({ message }),
      })

      if (!res.ok) {
        // 非流式错误（4xx/5xx），读 JSON detail
        let detail = `请求失败（${res.status}）`
        try {
          const body = await res.json()
          detail = body.detail || detail
        } catch { /* 忽略非 JSON 错误体 */ }
        throw new Error(detail)
      }
      if (!res.body) throw new Error('浏览器不支持流式响应')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done: streamDone } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })

        // SSE 事件以空行分隔，逐条解析
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const event = parseSSE(raw)
          if (event) {
            if (event.event === 'message') {
              handlers.delta?.(event.data?.delta || '')
            } else if (event.event === 'done') {
              handlers.done?.(event.data)
            }
          }
        }
      }
    } catch (e) {
      error.value = e.message || '网络异常，请稍后重试'
      throw e
    } finally {
      streaming.value = false
    }
  }

  return { streaming, error, onMessage, send }
}

function parseSSE(raw) {
  const lines = raw.split('\n')
  let event = 'message' // 默认事件名
  let data = ''
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  if (!data) return null
  try {
    return { event, data: JSON.parse(data) }
  } catch {
    return { event, data: { delta: data } }
  }
}
