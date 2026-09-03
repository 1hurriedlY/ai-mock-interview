<template>
  <div class="home-view">
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
          <div v-else class="upload-row">
            <input id="resume-file" type="file" accept=".pdf,.docx,.txt,.md" @change="onFileChange" />
            <button class="btn btn-secondary" :disabled="!file || uploading" @click="uploadResume">
              {{ uploading ? '解析中…' : '上传并解析' }}
            </button>
          </div>
        </div>

        <div class="zone">
          <div class="zone-head">
            <h2>岗位与面试官</h2>
          </div>
          <div class="field">
            <input
              v-model.trim="jobTitle"
              placeholder="目标岗位，例如 Python 后端工程师"
              @keyup.enter="startInterview"
            />
          </div>
          <div class="roles">
            <button
              v-for="r in roles"
              :key="r.key"
              class="role"
              :class="{ active: role === r.key }"
              @click="role = r.key"
            >
              <strong>{{ r.name }}</strong>
              <span>{{ r.description }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="divider"></div>

      <!-- 主操作 -->
      <div class="action-row">
        <p class="action-hint">准备好后开始，途中可随时语音回答、开启表情分析。</p>
        <button class="btn btn-primary btn-lg" :disabled="!jobTitle || starting" @click="startInterview">
          {{ starting ? '准备中…' : '开始面试' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { interviewApi, resumeApi } from '../api'

const router = useRouter()
const roles = ref([])
const role = ref('technical')

const file = ref(null)
const uploading = ref(false)
const resume = ref({})

const jobTitle = ref('')
const starting = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    roles.value = await interviewApi.roles()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载面试官角色失败'
  }
})

function onFileChange(e) {
  file.value = e.target.files?.[0] || null
}

async function uploadResume() {
  if (!file.value || uploading.value) return
  uploading.value = true
  error.value = ''
  try {
    const data = await resumeApi.upload(file.value)
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
  starting.value = true
  error.value = ''
  try {
    const data = await interviewApi.start(jobTitle.value, role.value, resume.value.resume_id || '')
    router.push({ name: 'interview', params: { id: data.session_id } })
  } catch (e) {
    error.value = e.response?.data?.detail || '开启面试失败，请稍后重试'
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.home-view { max-width: 1120px; margin: 0 auto; padding: 24px 32px 64px; }

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

/* 双栏：简历 | 岗位与面试官 */
.cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr);
  gap: 40px;
  align-items: start;
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
.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.upload-row input { font-size: 13px; color: var(--text-secondary); }

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

/* 角色选择：Lollipop 同款"选中态用浅色底" */
.roles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.role {
  text-align: left;
  padding: 16px 18px;
  background: var(--card);
  cursor: pointer;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  transition: var(--transition);
}
.role:hover { border-color: var(--ink); transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.role:active { transform: translateY(0) scale(0.985); }
.role strong { display: block; font-size: 15px; color: var(--ink); }
.role span { display: block; margin-top: 4px; font-size: 13px; color: var(--text-secondary); line-height: 1.55; }
.role.active {
  background: var(--ink-soft);
  border-color: var(--ink);
}
.role.active strong { color: var(--ink); }

/* 操作行 */
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.action-hint { color: var(--text-muted); font-size: 13px; }

@media (max-width: 900px) {
  .cols { grid-template-columns: 1fr; gap: 18px; }
}
@media (max-width: 640px) {
  .hero h1 { font-size: 24px; }
  .roles { grid-template-columns: 1fr; }
  .deck { padding: 18px 18px; }
}
</style>