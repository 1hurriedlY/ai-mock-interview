/* 用户头像：按用户名稳定生成（同名字永远同头像），无需上传存储。
 * 颜色取用户名哈希的色相；文字取名字前两个字符。
 */
export function initialsOf(name) {
  const s = String(name || '?').trim()
  if (!s) return '?'
  // 取前两个字符；英文名转为大写
  return s.slice(0, 2).toUpperCase()
}

export function avatarStyle(name) {
  const s = String(name || 'x')
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0
  }
  const hue = h % 360
  return {
    background: `linear-gradient(135deg, hsl(${hue} 72% 60%), hsl(${(hue + 42) % 360} 68% 46%))`,
  }
}
