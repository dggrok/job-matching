import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const KEY = 'jm-favorites-v1'

function load(): string[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw) as string[]
  } catch {
    // ignore
  }
  return []
}

/** 收藏的职位 id(形如 guokao-2026:002000:100110001001),只存本地。 */
export const useFavoritesStore = defineStore('favorites', () => {
  const ids = ref<string[]>(load())
  watch(ids, (v) => localStorage.setItem(KEY, JSON.stringify(v)), { deep: true })

  function has(id: string): boolean {
    return ids.value.includes(id)
  }

  function toggle(id: string): void {
    const i = ids.value.indexOf(id)
    if (i >= 0) ids.value.splice(i, 1)
    else ids.value.push(id)
  }

  return { ids, has, toggle }
})
