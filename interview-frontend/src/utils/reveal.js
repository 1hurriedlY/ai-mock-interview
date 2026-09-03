/* 滚动浮现工具：容器内所有 [data-reveal] 元素在进入视口时补 .reveal-in（淡入上移）。
 * - IntersectionObserver 为主；另加 rAF 滚动兜底，避免瞬间滚动/锚点跳转漏触发
 * - 触发一次即取消观察；全部触发后清理监听
 * - 不支持 IntersectionObserver 时直接全部显示（无 JS 动画降级）
 * - 动效开关：样式层尊重 prefers-reduced-motion（reveal-in 仍会显示，只是无过渡）
 */
export function bindReveal(root) {
  if (!root) return null
  const targets = Array.from(root.querySelectorAll('[data-reveal]'))
  if (!targets.length) return null

  // 模板只需标 data-reveal；隐藏类统一在这里补，避免漏写 class="reveal"
  targets.forEach((el) => {
    if (!el.classList.contains('reveal')) el.classList.add('reveal')
  })

  const reveal = (el) => {
    el.classList.add('reveal-in')
    const idx = targets.indexOf(el)
    if (idx !== -1) targets.splice(idx, 1)
  }

  if (!('IntersectionObserver' in window)) {
    targets.forEach(reveal)
    return null
  }

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          reveal(entry.target)
          io.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.1, rootMargin: '0px 0px -4% 0px' }
  )
  targets.forEach((el) => io.observe(el))

  // 滚动兜底：视口内的元素即使被跳过采样也立即显示
  const onScroll = () => {
    requestAnimationFrame(() => {
      if (!targets.length) {
        window.removeEventListener('scroll', onScroll, true)
        return
      }
      const vh = window.innerHeight
      targets.forEach((el) => {
        const r = el.getBoundingClientRect()
        if (r.top < vh * 0.94 && r.bottom > 0) reveal(el)
      })
    })
  }
  window.addEventListener('scroll', onScroll, { passive: true, capture: true })
  // 首屏元素：等两帧（先让浏览器按 .reveal 隐藏态完成首绘）再浮现，保证入场动画可见
  const kick = () => requestAnimationFrame(() => requestAnimationFrame(onScroll))
  kick()

  return () => {
    io.disconnect()
    window.removeEventListener('scroll', onScroll, true)
  }
}
