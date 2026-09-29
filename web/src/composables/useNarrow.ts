import { onBeforeUnmount, onMounted, ref } from 'vue'

/** 是否为窄屏(默认 720px 以下)。用于切换卡片布局、表单标签位置等。 */
export function useNarrow(maxWidth = 720) {
  const narrow = ref(typeof window !== 'undefined' ? window.innerWidth <= maxWidth : false)
  let mql: MediaQueryList | null = null
  const update = () => {
    if (mql) narrow.value = mql.matches
  }
  onMounted(() => {
    mql = window.matchMedia(`(max-width: ${maxWidth}px)`)
    narrow.value = mql.matches
    mql.addEventListener('change', update)
  })
  onBeforeUnmount(() => mql?.removeEventListener('change', update))
  return narrow
}
