<template>
  <div class="home-view" @click="activeMenu = null">
    <header class="hero">
      <h1>今天，练一场面试</h1>
      <p>备好简历、选好岗位与面试官，30 分钟内得到真实的问答练习与一份多维评分报告。</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="card deck">
      <!-- 双栏：简历 | 岗位与面试官 -->
      <div class="cols">
        <div class="zone">
          <div class="zone-head">
            <h2>简历（可选）</h2>
            <span v-if="resume.summary" class="chip chip-ok">已分析</span>
          </div>
          <p v-if="!resume.summary" class="zone-sub">不上传也能面试；上传后 AI 会围绕你的真实项目深入追问。</p>

          <div v-if="resume.summary" class="resume-done">
            <p class="resume-summary">{{ resume.summary }}</p>
            <button class="text-btn" @click="resume = {}">换一份简历</button>
          </div>
          <div
            v-else
            class="upload-zone"
            :class="{ dragging }"
            @click="pickFile"
            @keydown.enter="pickFile"
            role="button"
            tabindex="0"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
          >
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              class="hidden-input"
              @change="onFileChosen"
            />
            <span class="uz-plus">+</span>
            <span class="uz-main">{{ uploading ? '正在解析简历…' : '点击选择 / 拖入简历' }}</span>
            <span class="uz-sub">支持 PDF · Word · TXT · Markdown，选中后自动上传解析</span>
          </div>
        </div>

        <div class="zone">
          <div class="zone-head">
            <h2>面试配置</h2>
          </div>
          <div class="field">
            <input
              v-model.trim="jobTitle"
              placeholder="目标岗位，例如 Python 后端工程师"
              @keyup.enter="startInterview"
            />
          </div>

          <!-- 面试配置：难度 / 学历 / 面试官（点击弹下拉） -->
          <div class="cfg-row">
            <div v-for="cfg in cfgDefs" :key="cfg.key" class="cfg">
              <button type="button" class="cfg-btn" :class="{ on: activeMenu === cfg.key }" @click.stop="toggleMenu(cfg.key)">
                <span class="cfg-info">
                  <span class="cfg-cap">{{ cfg.label }}</span>
                  <span class="cfg-val">{{ currentVal(cfg.key) }}</span>
                </span>
                <span class="cfg-chev" :class="{ up: activeMenu === cfg.key }">▾</span>
              </button>
              <transition name="pop">
                <div v-if="activeMenu === cfg.key" class="cfg-menu card">
                  <button
                    v-for="o in optionsFor(cfg.key)"
                    :key="o.key"
                    type="button"
                    class="opt"
                    :class="{ on: selectedKey(cfg.key) === o.key }"
                    @click="choose(cfg.key, o.key)"
                  >
                    <span class="opt-txt">{{ o.label }}</span>
                    <span class="opt-ok">✓</span>
                  </button>
                </div>
              </transition>
            </div>
          </div>
          <p v-if="activeRoleDesc" class="role-tip">{{ activeRoleDesc }}</p>
          <p v-if="resume.summary" class="resume-linked">已关联简历 · 面试题将围绕你的技能与真实项目自动生成</p>
        </div>
      </div>

      <div class="divider"></div>

      <!-- 主操作 -->
      <div class="action-row">
        <div class="act-left">
          <p class="action-hint">准备好后开始，途中可随时语音回答、开启表情分析。</p>
          <p v-if="memberState.loaded" class="quota" :class="{ empty: quotaEmpty }">
            <template v-if="memberState.is_member">会员有效 · 面试不限场次（至 {{ memberState.member_until }}）</template>
            <template v-else-if="!quotaEmpty">免费体验剩余 <b>{{ memberState.free_interview.left }}</b> 场，会员不限场次</template>
            <template v-else>
              免费次数已用完
              <router-link class="go" to="/membership">开通会员 →</router-link>
            </template>
          </p>
        </div>
        <button class="btn btn-primary btn-lg" :disabled="!jobTitle || starting" @click="startInterview">
          {{ starting ? '准备中…' : '开始面试' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { interviewApi, resumeApi } from '../api'
import { Settings } from '../utils/settings'
import { memberState, refreshMember } from '../store/member'

const router = useRouter()

const roles = ref([])
const VALID_ROLES = ['technical', 'HR', 'stress']
const savedRole = Settings.get(Settings.keys.defaultRole)
const role = ref(VALID_ROLES.includes(savedRole) ? savedRole : 'technical')

// 面试配置：难度 / 学历
const difficulty = ref('medium')
const education = ref('any')
const difficulties = [
  { key: 'easy', label: '简单' },
  { key: 'medium', label: '中等' },
  { key: 'hard', label: '困难' },
]
const educations = [
  { key: 'any', label: '不限' },
  { key: 'college', label: '大专' },
  { key: 'bachelor', label: '本科' },
  { key: 'master', label: '硕士' },
]
const activeRoleDesc = computed(
  () => roles.value.find((r) => r.key === role.value)?.description || ''
)
// 免费额度是否耗尽（未加载完成时不算空，避免误拦）
const quotaEmpty = computed(
  () => memberState.loaded
    && !memberState.is_member
    && (memberState.free_interview?.left ?? 0) <= 0
)

// 面试配置下拉（难度 / 学历 / 面试官）
const ROLENAME_FALLBACK = { technical: '技术面', HR: 'HR 行为面', stress: '压力面' }
const cfgDefs = [
  { key: 'difficulty', label: '难度' },
  { key: 'education', label: '学历' },
  { key: 'role', label: '面试官' },
]
const activeMenu = ref(null)

function toggleMenu(key) {
  activeMenu.value = activeMenu.value === key ? null : key
}
function selectedKey(key) {
  if (key === 'difficulty') return difficulty.value
  if (key === 'education') return education.value
  return role.value
}
function optionsFor(key) {
  if (key === 'difficulty') return difficulties
  if (key === 'education') return educations
  return roles.value.map((r) => ({ key: r.key, label: r.name }))
}
function currentVal(key) {
  const sel = selectedKey(key)
  if (key === 'role') {
    return roles.value.find((r) => r.key === role.value)?.name
      || ROLENAME_FALLBACK[sel]
      || sel
  }
  return (key === 'difficulty' ? difficulties : educations).find((o) => o.key === sel)?.label || sel
}
function choose(key, val) {
  if (key === 'difficulty') difficulty.value = val
  else if (key === 'education') education.value = val
  else role.value = val
  activeMenu.value = null
}

const fileInput = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const resume = ref({})

const jobTitle = ref('')
const starting = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    roles.value = await interviewApi.roles()
    refreshMember()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载面试官角色失败'
  }
})

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onFileChosen(e) {
  const f = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!f || uploading.value) return
  uploadResume(f)
}

function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f && !uploading.value) uploadResume(f)
}

async function uploadResume(file) {
  if (!file || uploading.value) return
  uploading.value = true
  error.value = ''
  try {
    const data = await resumeApi.upload(file)
    resume.value = data.analysis || {}
    resume.value.resume_id = data.resume_id
  } catch (e) {
    error.value = e.response?.data?.detail || '简历解析失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function startInterview() {
  if (!jobTitle.value || starting.value) return
  // 会员/额度预检：额度耗尽直接引导开通（后端仍有强校验兜底）
  if (quotaEmpty.value) {
    router.push({ name: 'membership' })
    return
  }
  starting.value = true
  error.value = ''
  try {
    const data = await interviewApi.start(
      jobTitle.value,
      role.value,
      resume.value.resume_id || '',
      { difficulty: difficulty.value, education: education.value }
    )
    // 成功后刷新一次剩余额度
    refreshMember()
    router.push({ name: 'interview', params: { id: data.session_id } })
  } catch (e) {
    error.value = e.response?.data?.detail || '开启面试失败，请稍后重试'
    if (e.response?.status === 402) {
      refreshMember()
      router.push({ name: 'membership' })
    }
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.home-view {
  max-width: 1120px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 48px 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero { text-align: left; margin-bottom: 22px; }
.hero h1 {
  font-size: 30px;
  font-weight: 780;
  letter-spacing: -0.015em;
  color: var(--ink);
  line-height: 1.2;
}
.hero p {
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: 15px;
  max-width: 68ch;
  line-height: 1.7;
}

/* "准备台"浮卡：半透明毛玻璃，背景渐变与涟漪透出 */
.deck {
  padding: 28px 32px;
  background: rgba(255, 255, 255, 0.56);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  backdrop-filter: blur(24px) saturate(160%);
}

/* 上下分块：简历（上）→ 岗位与面试官（下），块间细线分隔 */
.cols { display: block; }
.cols .zone + .zone {
  margin-top: 6px;
  padding-top: 24px;
  border-top: 1px solid var(--border-soft);
}
.zone { padding: 4px 0; }
.zone-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}
.zone-head h2 {
  font-size: 16.5px;
  font-weight: 700;
  letter-spacing: -0.005em;
  color: var(--ink);
}
.zone-sub {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 14px;
}
.divider {
  height: 1px;
  background: var(--border-soft);
  margin: 20px 0;
}

/* chip / status */
.chip {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
}
.chip-ok { background: var(--success-bg); color: var(--success-text); }

/* 简历区 */
.resume-done p {
  color: var(--text);
  font-size: 13.5px;
  line-height: 1.65;
  margin: 8px 0 2px;
}
.text-btn {
  background: none;
  border: none;
  color: var(--ink);
  cursor: pointer;
  font-size: 12.5px;
  padding: 0;
  font-weight: 600;
}
.text-btn:hover { text-decoration: underline; }

/* 简历上传区：整块可点击/可拖拽，选中即自动上传 */
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 14px;
  padding: 26px 20px;
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-card);
  background: var(--bg-soft);
  cursor: pointer;
  text-align: center;
  transition: var(--transition);
  user-select: none;
}
.upload-zone:hover,
.upload-zone.dragging {
  border-color: var(--ink);
  background: var(--card);
  box-shadow: var(--shadow-sm);
}
.upload-zone.dragging { transform: translateY(-1px); }
.upload-zone:focus-visible {
  outline: none;
  border-color: var(--ink);
  box-shadow: var(--ring);
}
.hidden-input { display: none; }
.uz-plus {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--ink);
  color: #fff;
  font-size: 20px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}
.upload-zone:hover .uz-plus {
  transform: scale(1.08);
  box-shadow: 0 8px 18px rgba(15, 17, 21, 0.2);
}
.uz-plus { transition: transform 0.18s var(--ease), box-shadow 0.18s var(--ease); }
.uz-main {
  font-size: 14.5px;
  font-weight: 650;
  color: var(--ink);
}
.uz-sub {
  font-size: 12.5px;
  color: var(--text-secondary);
}

/* 表单 */
.field { margin-top: 12px; }
.field input {
  width: 100%;
  height: 46px;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-soft);
  font-size: 15px;
  transition: var(--transition);
}
.field input:focus {
  outline: none;
  border-color: var(--ink);
  background: var(--card);
  box-shadow: var(--ring);
}
.field input::placeholder { color: var(--text-muted); }

/* 面试配置下拉：统一工具条样式 */
.cfg-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.62);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  padding: 5px;
  box-shadow: var(--shadow-sm);
}
.cfg { position: relative; padding: 5px 4px; }
.cfg + .cfg { border-left: 1px dashed var(--border-soft); }
.cfg-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 13px;
  padding: 8px 12px;
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
}
.cfg-btn:hover { background: var(--bg-soft); }
.cfg-btn.on { background: var(--ink-soft); border-color: rgba(15, 17, 21, 0.08); }
.cfg-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cfg-cap {
  font-size: 10.5px;
  font-weight: 650;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}
.cfg-val {
  font-size: 15px;
  font-weight: 750;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cfg-chev {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--bg-soft);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  transition: transform 0.18s var(--ease), background 0.18s var(--ease);
}
.cfg-btn:hover .cfg-chev { background: var(--card); color: var(--ink); }
.cfg-btn.on .cfg-chev { background: var(--ink); color: #fff; }
.cfg-chev.up { transform: rotate(180deg); }
.cfg-menu {
  position: absolute;
  top: calc(100% + 10px);
  left: 4px;
  min-width: 186px;
  z-index: 30;
  background: rgba(255, 255, 255, 0.97);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  border: 1px solid var(--border-soft);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  padding: 7px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.cfg-menu::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 26px;
  width: 11px;
  height: 11px;
  background: var(--card);
  border-left: 1px solid var(--border-soft);
  border-top: 1px solid var(--border-soft);
  transform: rotate(45deg);
}
.opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 13.5px;
  font-weight: 500;
  padding: 9px 11px;
  border-radius: 10px;
  cursor: pointer;
  transition: var(--transition);
}
.opt:hover { background: var(--bg-soft); color: var(--ink); }
.opt.on { background: var(--ink-soft); color: var(--ink); font-weight: 650; }
.opt-ok { color: var(--ink); font-size: 13px; opacity: 0; transform: scale(0.6); transition: opacity 0.15s var(--ease), transform 0.15s var(--ease); }
.opt.on .opt-ok { opacity: 1; transform: scale(1); }
.role-tip {
  margin: 8px 2px 0;
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.6;
}
.pop-enter-active, .pop-leave-active { transition: opacity 0.16s var(--ease), transform 0.16s var(--ease); }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-5px) scale(0.98); transform-origin: top left; }

/* 操作行 */
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.act-left { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.action-hint { color: var(--text-muted); font-size: 13px; }
.resume-linked {
  margin: 10px 2px 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--success);
}
.quota { color: var(--text-secondary); font-size: 12.5px; }
.quota b { color: var(--ink); font-weight: 700; }
.quota.empty { color: var(--danger); }
.go {
  color: var(--ink); font-weight: 650; text-decoration: none;
  border-bottom: 1px dashed currentColor; margin-left: 2px;
}
.go:hover { color: var(--danger); border-color: var(--danger); }

@media (max-width: 640px) {
  .hero h1 { font-size: 24px; }
  .cfg-row { grid-template-columns: 1fr; }
  .cfg + .cfg { border-left: none; border-top: 1px dashed var(--border-soft); }
  .deck { padding: 18px 18px; }
}
</style>