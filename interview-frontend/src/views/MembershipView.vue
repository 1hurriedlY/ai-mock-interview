<template>
  <div class="member-view">
    <div class="head">
      <div>
        <h1>会员中心</h1>
        <p class="sub">免费体验 3 场面试；会员不限场次、不限导出、行业/求职全解锁。</p>
      </div>
      <router-link class="ghost" to="/home">返回首页</router-link>
    </div>

    <p v-if="okMsg" class="ok">{{ okMsg }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 我的状态 -->
    <section class="card status" :class="{ member: memberState.is_member }">
      <template v-if="memberState.is_member">
        <div class="big">会员有效</div>
        <p class="desc">到期时间：<b>{{ memberState.member_until }}</b> · 面试不限次 · 导出不限次</p>
      </template>
      <template v-else>
        <div class="big">免费额度</div>
        <p class="desc">
          模拟面试剩余 <b>{{ memberState.free_interview?.left ?? 0 }}</b> / {{ memberState.free_interview?.total ?? 3 }} 场
          · 报告导出剩余 <b>{{ memberState.free_export?.left ?? 0 }}</b> / {{ memberState.free_export?.total ?? 2 }} 次
        </p>
      </template>
      <button class="ghost" @click="reload">刷新状态</button>
    </section>

    <!-- 套餐 -->
    <section class="plans">
      <div v-for="p in plans" :key="p.key" class="card plan">
        <h2>{{ p.name }}</h2>
        <p class="days">开通 {{ p.days }} 天 · 面试/导出不限次</p>
        <p class="price">¥{{ yuan(p.price_cents) }}<span>/{{ p.days }}天</span></p>
        <button class="btn buy" :disabled="buying === p.key" @click="buy(p)">
          {{ buying === p.key ? '创建订单中…' : '立即开通' }}
        </button>
      </div>
    </section>

    <!-- 兑换码 -->
    <section class="card redeem">
      <h2>兑换码开通</h2>
      <p class="desc2">输入管理员发放的兑换码（如 MB-XXXXX-XXXXX）</p>
      <div class="row">
        <input v-model.trim="code" class="input" placeholder="MB-XXXXX-XXXXX" @keyup.enter="redeem" />
        <button class="btn" :disabled="!code || redeeming" @click="redeem">{{ redeeming ? '兑换中…' : '兑换' }}</button>
      </div>
    </section>

    <!-- 模拟收银台 -->
    <div v-if="cashier" class="overlay" @click.self="cashier = null">
      <div class="modal card">
        <h2>模拟收银台</h2>
        <p class="order-no">订单号 #{{ cashier.order_id }}</p>
        <p class="price-lg">¥{{ yuan(cashier.amount_cents) }}</p>
        <p class="muted2">{{ cashier.plan_name }} · 开通 {{ cashier.grant_days }} 天</p>
        <div class="btns">
          <button class="ghost" @click="cashier = null">取消</button>
          <button class="btn" :disabled="paying" @click="pay">{{ paying ? '支付中…' : '确认支付（模拟）' }}</button>
        </div>
        <p class="muted2">本期为模拟支付：点确认即完成，不会产生真实扣费。</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { memberApi } from '../api'
import { memberState, refreshMember } from '../store/member'

const error = ref('')
const okMsg = ref('')
const code = ref('')
const redeeming = ref(false)
const buying = ref('')
const paying = ref(false)
const cashier = ref(null) // { order_id, amount_cents, plan_name, grant_days }

const plans = computed(() => {
  const p = memberState.plans
  if (p && p.length) return p
  return [
    { key: 'month', name: '月度会员', days: 30, price_cents: 990 },
    { key: 'year', name: '年度会员', days: 365, price_cents: 9900 },
  ]
})

function yuan(c) {
  return (c / 100).toFixed(2)
}

function reload() {
  return refreshMember()
}

async function buy(plan) {
  error.value = ''
  buying.value = plan.key
  try {
    const order = await memberApi.createOrder(plan.key)
    cashier.value = {
      order_id: order.order_id,
      amount_cents: order.amount_cents,
      plan_name: order.plan_name,
      grant_days: order.grant_days,
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '下单失败'
  } finally {
    buying.value = ''
  }
}

async function pay() {
  if (!cashier.value) return
  paying.value = true
  error.value = ''
  try {
    await memberApi.mockPay(cashier.value.order_id)
    const st = await refreshMember()
    okMsg.value = `支付成功，会员已开通至 ${st.member_until}`
    cashier.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || '支付失败'
  } finally {
    paying.value = false
  }
}

async function redeem() {
  if (!code.value) return
  redeeming.value = true
  error.value = ''
  okMsg.value = ''
  try {
    const r = await memberApi.redeem(code.value)
    await refreshMember()
    okMsg.value = `兑换成功：开通 ${r.days} 天，会员至 ${r.member_until}`
    code.value = ''
  } catch (e) {
    error.value = e.response?.data?.detail || '兑换失败'
  } finally {
    redeeming.value = false
  }
}

onMounted(() => {
  if (!memberState.loaded) refreshMember()
})
</script>

<style scoped>
.member-view { max-width: 860px; margin: 0 auto; padding: 24px 24px 64px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
.head h1 { font-size: 26px; font-weight: 780; letter-spacing: -0.015em; color: var(--ink); }
.sub { color: var(--text-secondary); font-size: 14px; margin-top: 6px; }
.ok { color: var(--success-text); background: var(--success-bg); padding: 8px 14px; border-radius: 10px; font-size: 13.5px; margin-bottom: 12px; }
.error { color: var(--danger); margin-bottom: 12px; }

.card { background: var(--card); border: 1px solid var(--border-soft); border-radius: var(--radius-card); box-shadow: var(--shadow-sm); padding: 18px 20px; }
.ghost {
  border: 1px solid var(--border); background: var(--card); color: var(--text-secondary);
  font-size: 13px; padding: 8px 16px; border-radius: var(--radius-chip); cursor: pointer;
  text-decoration: none; transition: var(--transition);
}
.ghost:hover { color: var(--ink); border-color: var(--ink); }
.status { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.status .big { font-size: 22px; font-weight: 780; color: var(--ink); }
.status.member .big { color: var(--success-text); }
.desc { color: var(--text-secondary); font-size: 14px; margin: 4px 0; }
.desc b { color: var(--ink); }

.plans { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin: 16px 0; }
.plan { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.plan h2 { font-size: 17px; font-weight: 740; color: var(--ink); margin: 0; }
.days { color: var(--text-secondary); font-size: 13px; }
.price { font-size: 30px; font-weight: 800; color: var(--ink); margin: 4px 0 10px; }
.price span { font-size: 13px; color: var(--text-muted); font-weight: 500; }
.btn {
  border: 1px solid var(--ink); background: var(--ink); color: #fff;
  font-size: 14px; font-weight: 600; padding: 10px 22px; border-radius: var(--radius-chip);
  cursor: pointer; transition: var(--transition);
}
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn:hover:not(:disabled) { box-shadow: 0 8px 18px rgba(15, 17, 21, 0.16); }

.redeem .row { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.input {
  flex: 1; min-width: 220px; height: 42px; padding: 0 14px;
  border: 1px solid var(--border); border-radius: var(--radius-input);
  font-size: 14px; letter-spacing: 0.04em; transition: var(--transition);
}
.input:focus { outline: none; border-color: var(--ink); box-shadow: var(--ring); }
.desc2 { font-size: 13px; color: var(--text-muted); margin: 2px 0 0; }

.overlay { position: fixed; inset: 0; background: rgba(15, 17, 21, 0.4); backdrop-filter: blur(3px); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 24px; }
.modal { width: min(360px, 100%); text-align: center; }
.modal h2 { font-size: 18px; color: var(--ink); margin: 0 0 6px; }
.order-no { color: var(--text-muted); font-size: 12.5px; }
.price-lg { font-size: 40px; font-weight: 800; color: var(--ink); margin: 10px 0 2px; }
.muted2 { color: var(--text-muted); font-size: 13px; margin: 6px 0; }
.btns { display: flex; gap: 10px; justify-content: center; margin-top: 16px; }
</style>
