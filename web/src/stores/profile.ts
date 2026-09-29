import { defineStore } from 'pinia'
import { computed, reactive, watch } from 'vue'
import type { Profile } from '@/engine/types'

const KEY = 'jm-profile-v1'

/**
 * 默认画像:本科、电子信息工程(080701)。出生年月必须由用户填写,
 * 因为年龄界限精确到月,不能只凭"多少岁"判断。
 */
export function defaultProfile(): Profile {
  return {
    highestEdu: '本科',
    hasDegree: true,
    ugMajorId: 'UG:080701',
    pgMajorId: null,
    freshStatus: 'none',
    birth: '',
    gender: '',
    political: 'masses',
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
    if (!profile.birth) out.push('出生年月')
    if (level.value === 'UG' && !profile.ugMajorId) out.push('本科专业')
    if (level.value === 'PG' && !profile.pgMajorId) out.push('研究生专业')
    return out
  })

  function reset(): void {
    Object.assign(profile, defaultProfile())
  }

  return { profile, level, missing, reset }
})
