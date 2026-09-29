<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import PositionCard from '@/components/PositionCard.vue'
import PositionDrawer from '@/components/PositionDrawer.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useNarrow } from '@/composables/useNarrow'
import { applyFilters, emptyFilters, sortRows, toCsv, type Filters, type Row, type SortKey } from '@/engine/filters'
import type { Status } from '@/engine/types'
import { useDataStore } from '@/stores/data'
import { useFavoritesStore } from '@/stores/favorites'
import { useMatchStore } from '@/stores/match'
import { useProfileStore } from '@/stores/profile'

const data = useDataStore()
const favs = useFavoritesStore()
const match = useMatchStore()
const profileStore = useProfileStore()
const narrow = useNarrow(860)

const rows = computed(() => match.rows)
const summary = computed(() => match.summary)

const filters = reactive<Filters>(emptyFilters())
const sortKey = ref<SortKey>('headcount')
const page = ref(1)
const pageSize = ref(30)
const showMore = ref(false)

const VIEW_KEY = 'jm-view'
const viewMode = ref<'cards' | 'table'>(localStorage.getItem(VIEW_KEY) === 'table' ? 'table' : 'cards')
watch(viewMode, (v) => localStorage.setItem(VIEW_KEY, v))
/** 窄屏下表格不可读,强制使用卡片 */
const view = computed(() => (narrow.value ? 'cards' : viewMode.value))

const filtered = computed(() => sortRows(applyFilters(rows.value, filters), sortKey.value))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const filteredHeadcount = computed(() => filtered.value.reduce((s, r) => s + r.pos.headcount, 0))

watch([filters, sortKey, pageSize], () => (page.value = 1), { deep: true })

function options(pick: (r: Row) => string): { value: string; count: number }[] {
  const m = new Map<string, number>()
  for (const r of rows.value) {
    if (r.result.status === 'no') continue
    const k = pick(r)
    m.set(k, (m.get(k) ?? 0) + 1)
  }
  return [...m.entries()].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count)
}
const provinceOptions = computed(() => options((r) => r.province))
const sheetOptions = computed(() => options((r) => r.pos.sheet))
const levelOptions = computed(() => options((r) => r.pos.orgLevel))
const attrOptions = computed(() => options((r) => r.pos.attr))

/** 「更多筛选」里已启用的条件数,显示在按钮角标上 */
const moreCount = computed(
  () => [filters.sheets, filters.orgLevels, filters.attrs].filter((l) => l.length).length + (filters.minHeadcount > 0 ? 1 : 0),
)

const STATUS_ORDER: Status[] = ['ok', 'maybe', 'no']
function toggleStatus(s: Status) {
  const i = filters.statuses.indexOf(s)
  if (i >= 0) filters.statuses.splice(i, 1)
  else filters.statuses = STATUS_ORDER.filter((x) => filters.statuses.includes(x) || x === s)
}

function resetFilters() {
  Object.assign(filters, emptyFilters())
}

const drawerOpen = ref(false)
const current = ref<Row | null>(null)
function openRow(row: Row) {
  current.value = row
  drawerOpen.value = true
}

function briefReasons(row: Row): string {
  return row.result.reasons
    .filter((r) => r.level !== 'pass')
    .slice(0, 2)
    .map((r) => `${r.field}:${r.text}`)
    .join(';')
}

function majorText(row: Row): string {
  return data.examData?.majorRules[row.pos.majorId]?.text ?? ''
}

function exportCsv() {
  const csv = toCsv(filtered.value, (p) => data.examData?.majorRules[p.majorId]?.text ?? '')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `匹配结果-${data.examId}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const STATS: { key: Status; label: string; hint: string }[] = [
  { key: 'ok', label: '符合', hint: '所有条件明确满足' },
  { key: 'maybe', label: '待确认', hint: '有条件需人工核对' },
  { key: 'no', label: '不符合', hint: '至少一项明确不满足' },
]
function statNumber(k: Status) {
  return summary.value[k]
}
function statHeadcount(k: Status) {
  if (k === 'ok') return `招录 ${summary.value.okHeadcount} 人`
  if (k === 'maybe') return `招录 ${summary.value.maybeHeadcount} 人`
  return `共 ${rows.value.length} 个职位中`
}
</script>

<template>
  <div class="page">
    <el-alert
      v-if="data.exam?.sample"
      type="info"
      show-icon
      :closable="false"
      class="notice"
      title="当前使用的是 2026 年度国考职位表(开发样本)"
      description="2027 年度职位表预计 2026-10-14 发布,发布后导入数据管线即可切换。年龄、应届届别等条件请以当年公告为准。"
    />
    <el-alert v-if="profileStore.missing.length" type="warning" show-icon :closable="false" class="notice">
      <template #title>
        还缺少「{{ profileStore.missing.join('、') }}」,结果不够准确。
        <router-link to="/profile">去填写</router-link>
      </template>
    </el-alert>

    <!-- 概览带:标题与三态统计 -->
    <section class="hero rise">
      <div class="hero-text">
        <div class="eyebrow">匹配结果</div>
        <h1 class="page-title">你可以报考的岗位</h1>
        <p class="muted">
          {{ data.exam?.year }} 年度国考 · 共 {{ rows.length }} 个职位,已按「我的条件」逐条比对。点击右侧数字可显示或隐藏对应状态。
        </p>
      </div>
      <div class="stats">
        <button
          v-for="s in STATS"
          :key="s.key"
          type="button"
          class="stat"
          :class="[s.key, { off: !filters.statuses.includes(s.key) }]"
          :title="s.hint"
          @click="toggleStatus(s.key)"
        >
          <span class="num">{{ statNumber(s.key) }}</span>
          <StatusTag :status="s.key" size="sm" />
          <span class="sub">{{ statHeadcount(s.key) }}</span>
        </button>
      </div>
    </section>

    <!-- 筛选栏:桌面端吸顶 -->
    <section class="bar rise" style="--i: 1">
      <div class="bar-main">
        <el-input v-model="filters.keyword" clearable placeholder="搜索部门、职位、地点、职位代码" class="kw" />
        <el-select
          v-model="filters.provinces"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          filterable
          placeholder="工作省份"
          class="sel"
        >
          <el-option v-for="o in provinceOptions" :key="o.value" :value="o.value" :label="`${o.value}(${o.count})`" />
        </el-select>
        <el-select v-model="sortKey" class="sel sort">
          <el-option value="headcount" label="人数多的在前" />
          <el-option value="org" label="按部门名称" />
          <el-option value="status" label="按匹配状态" />
        </el-select>
        <el-button :type="showMore || moreCount ? 'primary' : 'default'" plain @click="showMore = !showMore">
          更多筛选<template v-if="moreCount"> · {{ moreCount }}</template>
        </el-button>
        <el-radio-group v-if="!narrow" v-model="viewMode" class="view-toggle">
          <el-radio-button value="cards">卡片</el-radio-button>
          <el-radio-button value="table">表格</el-radio-button>
        </el-radio-group>
      </div>

      <el-collapse-transition>
        <div v-show="showMore" class="bar-more">
          <label>
            <span>机关类别</span>
            <el-select v-model="filters.sheets" multiple collapse-tags collapse-tags-tooltip clearable placeholder="不限">
              <el-option v-for="o in sheetOptions" :key="o.value" :value="o.value" :label="`${o.value}(${o.count})`" />
            </el-select>
          </label>
          <label>
            <span>机构层级</span>
            <el-select v-model="filters.orgLevels" multiple collapse-tags collapse-tags-tooltip clearable placeholder="不限">
              <el-option v-for="o in levelOptions" :key="o.value" :value="o.value" :label="`${o.value}(${o.count})`" />
            </el-select>
          </label>
          <label>
            <span>职位属性</span>
            <el-select v-model="filters.attrs" multiple collapse-tags collapse-tags-tooltip clearable placeholder="不限">
              <el-option v-for="o in attrOptions" :key="o.value" :value="o.value" :label="`${o.value}(${o.count})`" />
            </el-select>
          </label>
          <label>
            <span>招录人数不少于</span>
            <el-input-number v-model="filters.minHeadcount" :min="0" :max="200" controls-position="right" />
          </label>
        </div>
      </el-collapse-transition>

      <div class="bar-foot">
        <span class="count">
          当前列出 <b>{{ filtered.length }}</b> 个职位,合计招录 <b>{{ filteredHeadcount }}</b> 人
        </span>
        <span class="bar-actions">
          <el-button link @click="resetFilters">重置筛选</el-button>
          <el-button link type="primary" :disabled="!filtered.length" @click="exportCsv">导出 CSV</el-button>
        </span>
      </div>
    </section>

    <!-- 卡片视图 -->
    <div v-if="view === 'cards' && paged.length" class="grid">
      <PositionCard
        v-for="(r, i) in paged"
        :key="r.pos.id"
        class="rise"
        :style="{ '--i': Math.min(i, 8) }"
        :row="r"
        :major-text="majorText(r)"
        :fav="favs.has(r.pos.id)"
        @open="openRow(r)"
        @toggle-fav="favs.toggle(r.pos.id)"
      />
    </div>

    <!-- 表格视图 -->
    <div v-else-if="view === 'table' && paged.length" class="table-wrap paper-card">
      <el-table :data="paged" row-key="pos.id" @row-click="openRow">
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }"><StatusTag :status="row.result.status" size="sm" /></template>
        </el-table-column>
        <el-table-column label="部门 / 职位" min-width="250">
          <template #default="{ row }">
            <div class="t-org">{{ row.pos.org }}<span v-if="row.pos.unit"> · {{ row.pos.unit }}</span></div>
            <div class="t-title">{{ row.pos.title }}</div>
            <div class="muted">{{ row.pos.sheet }} · {{ row.pos.code }}</div>
          </template>
        </el-table-column>
        <el-table-column label="地点" prop="pos.location" width="150" />
        <el-table-column label="人数" prop="pos.headcount" width="64" align="center" />
        <el-table-column label="学历" prop="pos.eduText" width="130" />
        <el-table-column label="专业要求" min-width="220">
          <template #default="{ row }">
            <el-tooltip :content="majorText(row)" placement="top" :show-after="300" popper-class="wide-tip">
              <div class="clamp">{{ majorText(row) }}</div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="需要注意" min-width="240">
          <template #default="{ row }">
            <div class="clamp warn">{{ row.result.status === 'ok' ? '—' : briefReasons(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openRow(row)">详情</el-button>
            <el-button link :type="favs.has(row.pos.id) ? 'warning' : 'info'" @click.stop="favs.toggle(row.pos.id)">
              {{ favs.has(row.pos.id) ? '已藏' : '收藏' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-empty
      v-else
      class="empty paper-card"
      description="没有符合当前筛选的职位。可以调整「我的条件」或放宽筛选,也可以点击上方数字显示「待确认」和「不符合」查看原因。"
    />

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="filtered.length"
      :page-sizes="[30, 50, 100]"
      :layout="narrow ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'"
      :pager-count="narrow ? 5 : 7"
      background
      class="pager"
    />

    <PositionDrawer v-model="drawerOpen" :row="current" />
  </div>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
}

/* 概览带 */
.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 32px;
  padding: 8px 0 24px;
  border-bottom: 2px solid var(--ink);
  margin-bottom: 20px;
  position: relative;
}
.hero::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -6px;
  border-bottom: 1px solid var(--ink);
}
.hero-text {
  max-width: 460px;
}
.hero-text p {
  margin: 0;
  line-height: 1.7;
}

.stats {
  display: flex;
  align-items: stretch;
}
.stat {
  --c: var(--no);
  font: inherit;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  min-width: 150px;
  padding: 4px 28px;
  text-align: left;
  color: var(--ink);
  border-left: 1px dashed var(--line-strong);
  transition: opacity 0.2s, transform 0.2s;
}
.stat:first-child {
  border-left: none;
}
.stat:hover {
  transform: translateY(-2px);
}
.stat.ok {
  --c: var(--ok);
}
.stat.maybe {
  --c: var(--maybe);
}
.stat .num {
  font-family: var(--font-serif);
  font-size: 50px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.01em;
  color: var(--c);
}
.stat .sub {
  font-size: 12px;
  color: var(--ink-3);
}
.stat.off {
  opacity: 0.35;
}
.stat.off .num {
  text-decoration: line-through;
  text-decoration-thickness: 2px;
}

/* 筛选栏 */
.bar {
  position: sticky;
  top: 68px;
  z-index: 20;
  margin-bottom: 20px;
  padding: 14px 16px 10px;
  background: rgba(255, 253, 247, 0.96);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
}
.bar-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.kw {
  flex: 1 1 260px;
  min-width: 200px;
}
.sel {
  width: 190px;
}
.sel.sort {
  width: 140px;
}
.view-toggle {
  margin-left: auto;
}
.bar-more {
  display: flex;
  flex-wrap: wrap;
  gap: 14px 20px;
  margin-top: 12px;
  padding: 14px 0 6px;
  border-top: 1px dashed var(--line-strong);
}
.bar-more label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 210px;
}
.bar-more label span {
  font-size: 12px;
  color: var(--ink-3);
  letter-spacing: 0.08em;
}
.bar-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 13px;
  color: var(--ink-3);
}
.count b {
  color: var(--navy);
  font-family: var(--font-serif);
  font-size: 15px;
}

/* 卡片网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 500px), 1fr));
  gap: 16px;
}

/* 表格 */
.table-wrap {
  overflow: hidden;
}
.t-org {
  font-size: 13px;
  color: var(--ink-3);
}
.t-title {
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 15px;
  margin: 2px 0;
}
.clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  font-size: 13px;
}
.warn {
  color: var(--maybe);
}
:deep(.el-table__row) {
  cursor: pointer;
}

.empty {
  padding: 40px 16px;
}
.pager {
  margin-top: 24px;
  justify-content: center;
}

@media (max-width: 1080px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  .hero-text {
    max-width: none;
  }
}

@media (max-width: 860px) {
  .bar {
    position: static;
  }
  .sel,
  .sel.sort {
    flex: 1 1 140px;
    width: auto;
  }
  .stat {
    min-width: 0;
    padding: 4px 16px;
  }
  .stat .num {
    font-size: 36px;
  }
  .stats {
    width: 100%;
  }
  .stat:first-child {
    padding-left: 0;
  }
  .bar-more label {
    width: 100%;
  }
}
</style>

<style>
.wide-tip {
  max-width: 520px;
  line-height: 1.6;
}
</style>
