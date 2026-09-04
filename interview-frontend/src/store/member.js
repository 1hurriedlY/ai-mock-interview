/* 会员状态单例：登录后 /member/status 的结果，供全局展示与额度提示。
 * 与 auth 相似，无 Pinia，直接 reactive + 方法。
 */
import { reactive } from 'vue'
import { memberApi } from '../api'

const empty = {
  is_member: false,
  member_until: '',
  free_interview: { total: 3, used: 0, left: 3 },
  free_export: { total: 2, used: 0, left: 2 },
  plans: [],
  loaded: false,
}

export const memberState = reactive({ ...empty })

export async function refreshMember() {
  try {
    const data = await memberApi.status()
    Object.assign(memberState, data, { loaded: true })
    return memberState
  } catch (e) {
    // token 失效等：保持空态不阻塞
    return memberState
  }
}

export function clearMember() {
  Object.assign(memberState, { ...empty })
}

export function memberLeft() {
  return memberState.is_member ? Infinity : (memberState.free_interview?.left ?? 0)
}
