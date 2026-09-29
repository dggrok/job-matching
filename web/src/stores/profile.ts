import { defineStore } from 'pinia'
import { computed, reactive, watch } from 'vue'
import type { Profile } from '@/engine/types'

// v2:去掉了写死的默认个人信息。旧版(v1)可能带着旧默认值,不再读取。
const KEY = 'jm-profile-v2'

/**
 * 默认画像:所有与个人相关的项都留空,由用户自己填写。
 * 未填写的项在匹配时一律按「待确认」处理,不会被当作符合或不符合。
 * 基层年限 0、无项目、无证书是"没有"的自然初值,不算个人信息假设。
 */
export function defaultProfile(): Profile {
  return {
    highestEdu: '',
    hasDegree: null,
    ugMajorId: null,
    pgMajorId: null,
    freshStatus: 'unknown',
    birth: '',
    gender: '',
    political: 'unknown',
    grassrootsYears: 0,
    projects: [],
    cet: 'unknown',
    hasAltEnglishCert: false,
    legalQualification: false,
    originProvince: '',
  }
}

function load(): Profile {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return { ...defaultProfile(), ...(JSON.parse(raw) as Partial<Profile>) }
  } catch {
    // 本地数据损坏时回退到默认值
  }
  return defaultProfile()
}

/** 用户画像:只保存在浏览器 localStorage,不上传。 */
export const useProfileStore = defineStore('profile', () => {
  const profile = reactive<Profile>(load())

  watch(profile, (v) => localStorage.setItem(KEY, JSON.stringify(v)), { deep: true })

  const level = computed<'UG' | 'PG'>(() => (profile.highestEdu === '硕士' || profile.highestEdu === '博士' ? 'PG' : 'UG'))

  /** 缺少哪些必填项;为空表示可以给出可靠结果。 */
  const missing = computed<string[]>(() => {
    const out: string[] = []
    if (!profile.highestEdu) out.push('最高学历')
    if (profile.hasDegree === null) out.push('学位情况')
    if (level.value === 'UG' && !profile.ugMajorId) out.push('本科专业')
    if (level.value === 'PG' && !profile.pgMajorId) out.push('研究生专业')
    if (profile.freshStatus === 'unknown') out.push('应届状态')
    if (!profile.birth) out.push('出生年月')
    if (profile.political === 'unknown') out.push('政治面貌')
    return out
  })

  function reset(): void {
    Object.assign(profile, defaultProfile())
  }

  return { profile, level, missing, reset }
})
