<template>
  <div ref="root" class="landing">
    <!-- 顶部导航（浮感毛玻璃） -->
    <header class="nav glass">
      <div class="brand">模拟面试 AI 助手</div>
      <nav class="nav-links">
        <a href="#steps">怎么练</a>
        <a href="#bonus">更多能力</a>
        <a href="#faq">常见问题</a>
      </nav>
      <div class="nav-cta">
        <button class="btn btn-secondary" @click="goLogin">登录</button>
        <button class="btn btn-primary" @click="goLogin">开始使用</button>
      </div>
    </header>

    <!-- 首屏 -->
    <section class="hero">
      <h1 data-reveal>每一次模拟面试，<br />都让你更接近 Offer</h1>
      <p class="lead" data-reveal style="--d: 90ms">
        从目标岗位梳理、简历解析，到真人感的 AI 模拟面试和结构化复盘，一站完成面试准备。
      </p>
      <div class="hero-cta" data-reveal style="--d: 180ms">
        <button class="btn btn-primary btn-lg" @click="goLogin">开始使用</button>
        <a class="btn btn-secondary btn-lg" href="#steps">先看看怎么练</a>
      </div>
      <p class="hero-note" data-reveal style="--d: 260ms">完全免费 · 无需安装 · 浏览器即开即用</p>
    </section>

    <!-- 四步练习流程 -->
    <section id="steps" class="band">
      <h2 class="band-title" data-reveal>不是泛泛练习，而是完整的面试准备</h2>
      <div class="steps">
        <div
          v-for="(s, i) in steps"
          :key="s.no"
          class="step-card"
          data-reveal
          :style="{ '--d': i * 90 + 'ms' }"
        >
          <span class="no">{{ s.no }}</span>
          <h3>{{ s.title }}</h3>
          <p>{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 更多能力 -->
    <section id="bonus" class="band alt">
      <h2 class="band-title" data-reveal>围绕真实面试场景的加分能力</h2>
      <div class="bonus-grid">
        <div
          v-for="(b, i) in bonus"
          :key="b.title"
          class="bonus-card"
          data-reveal
          :style="{ '--d': (i % 3) * 90 + 'ms' }"
        >
          <h3>{{ b.title }}</h3>
          <p>{{ b.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 收口 CTA -->
    <section class="cta-band">
      <h2 data-reveal>现在，开始你的第一次模拟面试</h2>
      <p data-reveal style="--d: 90ms">准备好一个目标岗位，3 分钟进入面试状态。</p>
      <div data-reveal style="--d: 180ms">
        <button class="btn btn-primary btn-lg" @click="goLogin">开始使用</button>
      </div>
    </section>

    <!-- FAQ -->
    <section id="faq" class="band">
      <h2 class="band-title" data-reveal>开始之前，你可能还想知道</h2>
      <details
        v-for="(q, i) in faqs"
        :key="q.q"
        class="faq"
        data-reveal
        :style="{ '--d': i * 60 + 'ms' }"
      >
        <summary>{{ q.q }}</summary>
        <p>{{ q.a }}</p>
      </details>
    </section>

    <footer class="foot">
      <span class="brand-mini">●‿● 模拟面试 AI 助手</span>
      <span>本地运行 · 数据仅存于你自己的服务器</span>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { bindReveal } from '../utils/reveal'

const router = useRouter()
const root = ref(null)

const steps = [
  { no: '01', title: '选岗位与面试官', desc: '输入目标岗位，选择技术面、项目面或 HR 面，AI 围绕该岗位出题。' },
  { no: '02', title: '上传简历（可选）', desc: '解析你的技能栈与项目经历，让提问围绕你的真实背景深入追问。' },
  { no: '03', title: '真人感模拟面试', desc: '支持打字或语音答题，可开摄像头做表情分析，AI 会像真人一样继续追问。' },
  { no: '04', title: '多维评分与复盘', desc: '五维能力雷达、岗位匹配度与逐题改进建议，还有参考要点对照学习。' },
]

const bonus = [
  { title: '行业调研', desc: '让 AI 生成目标行业的产业链、玩家、技能与面试题清单。' },
  { title: '求职渠道', desc: '按岗位生成适配的招聘平台清单与使用建议。' },
  { title: 'STAR 话术', desc: '把项目经历整理成可背诵的 STAR 讲项目话术。' },
  { title: '语音答题', desc: '支持边说边面，识别结束自动发送，训练口头表达。' },
  { title: '表情分析', desc: '实时情绪识别，报告中生成表情时间轴与点评。' },
  { title: '报告导出', desc: '评分报告可导出为 DOCX 或 PDF，方便存档与复盘。' },
]

const faqs = [
  { q: '需要安装什么吗？', a: '什么都不用装。后端部署好后打开网页即可使用，推荐用 Chrome 或 Edge 浏览器。' },
  { q: '收费吗？', a: '本项目完全免费自用。它部署在你自己电脑或服务器上，不产生平台会员费用。' },
  { q: '一次模拟面试怎么进行？', a: '选好岗位与面试官后进入对话，AI 出题、你作答，可语音可打字；结束后面试自动生成评分报告。' },
  { q: '简历、语音和摄像头数据安全吗？', a: '安全。所有数据只写入你自己的数据库，画面仅在本机处理，不会上传到任何第三方。' },
]

function goLogin() {
  router.push({ name: 'login', query: { redirect: '/home' } })
}

onMounted(() => {
  bindReveal(root.value)
})
</script>

<style scoped>
.landing {
  width: 100%;
  scroll-behavior: smooth;
}

/* 顶部导航 */
.nav {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 14px 36px;
  background: rgba(255, 255, 255, 0.66);
  -webkit-backdrop-filter: saturate(140%) blur(16px);
  backdrop-filter: saturate(140%) blur(16px);
  border-bottom: 1px solid var(--border-soft);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  color: var(--ink);
}
.brand::before {
  content: '●‿●';
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--ink);
  color: #fff;
  font-size: 14px;
}
.nav-links {
  display: flex;
  gap: 6px;
  margin-left: 8px;
}
.nav-links a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 550;
  padding: 7px 12px;
  border-radius: var(--radius-chip);
  transition: var(--transition);
}
.nav-links a:hover { color: var(--ink); background: var(--ink-soft); }
.nav-cta { margin-left: auto; display: flex; gap: 10px; }

/* 首屏 */
.hero {
  max-width: 900px;
  margin: 0 auto;
  padding: 92px 24px 72px;
  text-align: center;
}
.hero h1 {
  font-size: 52px;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.14;
  color: var(--ink);
}
.lead {
  margin: 20px auto 0;
  max-width: 56ch;
  color: var(--text-secondary);
  font-size: 17px;
  line-height: 1.8;
}
.hero-cta {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 34px;
}
.hero-note {
  margin-top: 18px;
  color: var(--text-muted);
  font-size: 13px;
}

/* 内容带 */
.band {
  max-width: 1080px;
  margin: 0 auto;
  padding: 56px 24px;
}
.band.alt {
  max-width: none;
  background: rgba(255, 255, 255, 0.5);
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
  padding: 56px 24px;
}
.band.alt .steps,
.band.alt .bonus-grid {
  max-width: 1080px;
  margin-left: auto;
  margin-right: auto;
}
.band.alt .band-title { max-width: 1080px; margin-left: auto; margin-right: auto; }
.band-title {
  text-align: center;
  font-size: 28px;
  font-weight: 780;
  letter-spacing: -0.015em;
  color: var(--ink);
  margin-bottom: 36px;
}

/* 步骤卡 */
.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.step-card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 24px 22px;
  transition: var(--transition);
}
.step-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.step-card .no {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
.step-card h3 {
  margin: 10px 0 8px;
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
}
.step-card p {
  color: var(--text-secondary);
  font-size: 13.5px;
  line-height: 1.75;
}

/* 亮点格 */
.bonus-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.bonus-card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 20px 22px;
}
.bonus-card h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 6px;
}
.bonus-card p {
  color: var(--text-secondary);
  font-size: 13.5px;
  line-height: 1.75;
  margin: 0;
}

/* 收口 CTA */
.cta-band {
  max-width: 1080px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  text-align: center;
}
.cta-band h2 {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.015em;
  color: var(--ink);
}
.cta-band p {
  margin: 12px auto 28px;
  color: var(--text-secondary);
  font-size: 15px;
}

/* FAQ */
.faq {
  max-width: 720px;
  margin: 0 auto 12px;
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 18px 22px;
}
.faq summary {
  cursor: pointer;
  font-size: 15px;
  font-weight: 650;
  color: var(--ink);
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after { content: '+'; color: var(--text-muted); font-size: 18px; }
.faq[open] summary::after { content: '−'; }
.faq p {
  margin: 12px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

/* 页脚 */
.foot {
  border-top: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.5);
  padding: 26px 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
  flex-wrap: wrap;
}
.brand-mini {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-weight: 600;
}

@media (max-width: 900px) {
  .nav { gap: 12px; padding: 12px 18px; flex-wrap: wrap; }
  .nav-links { display: none; }
  .hero h1 { font-size: 36px; }
  .steps { grid-template-columns: repeat(2, 1fr); }
  .bonus-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .steps { grid-template-columns: 1fr; }
  .bonus-grid { grid-template-columns: 1fr; }
  .band-title { font-size: 23px; }
}
</style>
