/* 打字机：把 SSE 事件流增量组装成当前回复文本。 */
import { ref } from 'vue'

export function useTypewriter() {
  const text = ref('')       // 当前完整文本
  const done = ref(false)    // 本次回复是否流完
  let buffer = ''            // 事件已推文本（与 text 同值，冗余便于事件回调用）

  function reset() {
    text.value = ''
    done.value = false
    buffer = ''
  }

  function appendDelta(delta) {
    buffer += delta
    text.value = buffer
  }

  function finish() {
    done.value = true
  }

  return { text, done, reset, appendDelta, finish }
}
