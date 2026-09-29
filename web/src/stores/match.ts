import { defineStore } from 'pinia'
import { computed } from 'vue'
import { regionOf, summarize, type Row } from '@/engine/filters'
import { matchPosition } from '@/engine/match'
import type { Profile } from '@/engine/types'
import { useDataStore } from './data'
import { useProfileStore } from './profile'

/**
 * 全量匹配结果的共享缓存。
 * computed 是惰性且带缓存的:只有画像或考试数据变化时才会重算(约 2 万条,百毫秒级),
 * 「匹配结果」「我的条件」等多个页面共用同一份结果。
 */
export const useMatchStore = defineStore('match', () => {
  const data = useDataStore()
  const profileStore = useProfileStore()

  const rows = computed<Row[]>(() => {
    const d = data.examData
    const exam = data.exam
    const catalog = data.catalog
    if (!d || !exam || !catalog) return []
    // 先深拷贝成普通对象,避免匹配时对响应式代理做上万次读取
    const profile = JSON.parse(JSON.stringify(profileStore.profile)) as Profile
    const ctx = { profile, exam, catalog, majorRules: d.majorRules, catRefs: d.catRefs }
    const kind = exam.kind
    return d.positions.map((pos) => ({ pos, result: matchPosition(pos, ctx), province: regionOf(pos.location, kind) }))
  })

  const summary = computed(() => summarize(rows.value))

  return { rows, summary }
})
