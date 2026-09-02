<template>
  <div class="home-view">
    <div class="hero">
      <h1>模拟面试 AI 助手</h1>
      <p>上传简历 → 选择岗位与面试官 → 开始一场真人感的模拟面试，结束后获得多维评分报告。</p>
    </div>

    <!-- ① 简历（可选） -->
    <section class="card">
      <div class="section-head">
        <h2>① 简历（可选，可跳过后仍能面试）</h2>
        <span v-if="resume.summary" class="tag ok">已分析</span>
      </div>
      <div v-if="resume.summary" class="resume-done">
        <p class="resume-summary">{{ resume.summary }}</p>
        <button class="link" @click="resume = {}">重新上传</button>
      </div>
      <div v-else>
        <div class="upload-row">
          <input type="file" accept=".pdf,.docx,.txt,.md" @change="onFileChange" />
          <button :disabled="!file || uploading" @click="uploadResume">
            {{ uploading ? '解析中…' : '上传并解析' }}
          </button>
        </div>
        <p class="hint">支持 PDF / DOCX / TXT，AI 会从简历提取技能栈与项目经历，用于深度追问。</p>
      </div>
    </section>

    <!-- ② 岗位与角色 -->
    <section class="card">
      <h2>② 面试准备</h2>
      <div class="form-row">
        <input v-model.trim="jobTitle" placeholder="目标岗位，如：Python 后端工程师" @keyup.enter="startInterview" />
      </div>
      <div class="roles">
        <button
          v-for="r in roles"
          :key="r.key"
          class="role-card"
          :class="{ active: role === r.key }"
          @click="role = r.key"
        >
          <strong>{{ r.name }}</strong>
          <span>{{ r.description }}</span>
        </button>
      </div>
      <button class="primary" :disabled="!jobTitle || starting" @click="startInterview">
        {{ starting ? '准备中…' : '开始面试' }}
      </button>
    </section>

    <p v-if="error" class="error">{{ error }}</p>
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
const resume = ref({}) // { resume_id, summary, skills }

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
.home-view { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
.hero h1 { color: var(--primary); margin-bottom: 8px; }
.hero p { color: var(--text-secondary); margin-bottom: 20px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}
.section-head { display: flex; align-items: center; gap: 10px; justify-content: space-between; }
.card h2 { font-size: 16px; margin-bottom: 14px; }
.tag.ok { background: #dcfce7; color: #166534; font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.resume-done p { color: var(--text); margin-bottom: 8px; font-size: 14px; }
.resume-summary { line-height: 1.7; }
.upload-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.upload-row input { font-size: 13px; }
.upload-row button, .primary {
  background: var(--primary); color: #fff; border: none; border-radius: 8px;
  padding: 10px 18px; cursor: pointer; font-size: 14px;
}
.upload-row button:disabled, .primary:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { color: var(--text-secondary); font-size: 12px; margin-top: 8px; }
.form-row { margin-bottom: 12px; }
.form-row input {
  width: 100%; padding: 10px 12px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px;
}
.roles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 14px; }
.role-card {
  border: 1px solid var(--border); background: #f9fafb; border-radius: 10px;
  padding: 12px; text-align: left; cursor: pointer; font-family: inherit;
}
.role-card strong { display: block; margin-bottom: 4px; }
.role-card span { font-size: 12px; color: var(--text-secondary); display: block; }
.role-card.active { border-color: var(--primary); background: #eff6ff; }
.role-card.active strong { color: var(--primary); }
.error { color: #dc2626; }
.link { background: none; border: none; color: var(--primary); cursor: pointer; text-decoration: underline; }
</style>
