/* 轻量用户设置：localStorage 持久化，键统一前缀 msi_。
 * 供头像小窗内的设置项读写，各页面按需读取。
 */
const P = 'msi_'

export const Settings = {
  keys: {
    bgFx: P + 'bgFx',           // 背景涟漪动效，默认开
    reduceMotion: P + 'reduceMotion', // 页面动效减弱，默认关
    autoSpeak: P + 'autoSpeak', // 面试回复自动朗读，默认关
    defaultRole: P + 'defaultRole',   // 首页默认面试官 technical/HR/stress
  },
  get(key) {
    return localStorage.getItem(key)
  },
  set(key, val) {
    localStorage.setItem(key, String(val))
  },
  isOn(key, fallback = false) {
    const v = localStorage.getItem(key)
    return v === null ? fallback : v === '1'
  },
}
