import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { Catalog } from '@/engine/catalog'
import type { CatalogFile, ExamData, ExamMeta, Manifest } from '@/engine/types'

const LAST_EXAM_KEY = 'jm-last-exam'

function dataUrl(path: string): string {
  return `${import.meta.env.BASE_URL}data/${path}`
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(dataUrl(path))
  if (!res.ok) throw new Error(`加载 ${path} 失败(HTTP ${res.status})`)
  return (await res.json()) as T
}

/** 数据仓库:manifest、专业目录、当前考试的职位数据。体量大,用 shallowRef 避免深度响应式。 */
export const useDataStore = defineStore('data', () => {
  const manifest = shallowRef<Manifest | null>(null)
  const catalog = shallowRef<Catalog | null>(null)
  const examData = shallowRef<ExamData | null>(null)
  const examId = ref<string>('')
  const loading = ref(false)
  const stage = ref('')
  const error = ref('')

  const exams = computed(() => manifest.value?.exams ?? [])
  const availableExams = computed(() => exams.value.filter((e) => !e.pending))
  const exam = computed<ExamMeta | null>(() => exams.value.find((e) => e.id === examId.value) ?? null)

  async function init(): Promise<void> {
    if (manifest.value) return
    loading.value = true
    error.value = ''
    try {
      stage.value = '加载考试清单与专业目录…'
      const [m, c] = await Promise.all([getJson<Manifest>('manifest.json'), getJson<CatalogFile>('catalog.json')])
      manifest.value = m
      catalog.value = new Catalog(c)
      const saved = localStorage.getItem(LAST_EXAM_KEY)
      const pick = m.exams.find((e) => e.id === saved && !e.pending) ?? m.exams.find((e) => !e.pending)
      if (!pick) throw new Error('没有可用的职位数据,请先运行数据管线构建')
      await selectExam(pick.id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
      stage.value = ''
    }
  }

  async function selectExam(id: string): Promise<void> {
    const meta = exams.value.find((e) => e.id === id)
    if (!meta || !meta.file) return
    loading.value = true
    try {
      stage.value = `加载${meta.name}职位数据(体积较大,首次需要几秒)…`
      examData.value = await getJson<ExamData>(meta.file)
      examId.value = id
      localStorage.setItem(LAST_EXAM_KEY, id)
    } finally {
      loading.value = false
      stage.value = ''
    }
  }

  return { manifest, catalog, examData, examId, exam, exams, availableExams, loading, stage, error, init, selectExam }
})
