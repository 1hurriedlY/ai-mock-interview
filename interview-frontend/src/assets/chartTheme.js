/* ECharts 统一视觉主题：数值与 src/style.css 的 CSS 变量保持一致（静态镜像）。
 * 图表在 JS 中拿不到 CSS 变量，故在此集中定义，供雷达图/表情图等共用，
 * 保证全站图表色板、字号、网格线风格统一。
 */
export const chartTheme = {
  // 主色（墨色单色，= --primary / --primary-hover）
  primary: '#1c2431',
  primaryDeep: '#000000',
  primaryArea: 'rgba(15, 23, 42, 0.08)',

  // 文本（= --text / --text-secondary / --text-muted，slate 系）
  text: '#1e293b',
  textSecondary: '#64748b',
  textMuted: '#94a3b8',

  // 网格线 / 分隔（= --border / --border-soft）
  splitLine: '#e2e8f0',
  splitArea: ['#f8fafc', '#eef1f6'],
  gridLine: '#eef1f6',

  // 语义色（= --success / --warning / --danger）
  success: '#16a34a',
  warning: '#d97706',
  danger: '#dc2626',

  // 字号
  fontSize: 12,
  axisFontSize: 11,

  // 表情 7 类统一色板（低饱和协调色；首色与墨色主题呼应）
  expressionPalette: ['#1c2431', '#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981', '#f43f5e', '#64748b'],
}

export default chartTheme
