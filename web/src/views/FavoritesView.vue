<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import StatusTag from '@/components/StatusTag.vue'
import { POLITICAL_LABEL, provinceOf, type Row } from '@/engine/filters'
import { matchPosition } from '@/engine/match'
import type { Profile } from '@/engine/types'
import { useDataStore } from '@/stores/data'
import { useFavoritesStore } from '@/stores/favorites'
import { useProfileStore } from '@/stores/profile'
import PositionDrawer from '@/components/PositionDrawer.vue'

const data = useDataStore()
const favs = useFavoritesStore()
const profileStore = useProfileStore()

const rows = computed<Row[]>(() => {
  const d = data.examData
  if (!d || !data.exam || !data.catalog) return []
  const profile = JSON.parse(JSON.stringify(profileStore.profile)) as Profile
  const ctx = { profile, exam: data.exam, catalog: data.catalog, majorRules: d.majorRules }
  const byId = new Map(d.positions.map((p) => [p.id, p]))
  return favs.ids
    .map((id) => byId.get(id))
    .filter((p): p is NonNullable<typeof p> => !!p)
    .map((pos) => ({ pos, result: matchPosition(pos, ctx), province: provinceOf(pos.location) }))
})

/** 收藏了但不属于当前考试年度的职位数,提示用户切换年度查看。 */
const otherExam = computed(() => favs.ids.length - rows.value.length)

const selected = ref<Row[]>([])
const compareOpen = ref(false)
const drawerOpen = ref(false)
const current = ref<Row | null>(null)

function onSelect(list: Row[]) {
  selected.value = list
}

function openCompare() {
  if (selected.value.length < 2) return ElMessage.warning('请至少选择 2 个职位')
  if (selected.value.length > 5) return ElMessage.warning('最多同时对比 5 个职位')
  compareOpen.value = true
}

function openRow(row: Row) {
  current.value = row
  drawerOpen.value = true
}

const majorText = (r: Row) => data.examData?.majorRules[r.pos.majorId]?.text ?? ''

interface CompareLine {
  label: string
  get: (r: Row) => string
}
const lines: CompareLine[] = [
  { label: '部门', get: (r) => r.pos.org },
  { label: '职位', get: (r) => r.pos.title },
  { label: '工作地点', get: (r) => r.pos.location },
  { label: '招考人数', get: (r) => String(r.pos.headcount) },
  { label: '学历', get: (r) => r.pos.eduText },
  { label: '专业要求', get: majorText },
  { label: '政治面貌', get: (r) => POLITICAL_LABEL[r.pos.political] ?? r.pos.political },
  { label: '基层年限', get: (r) => (r.pos.grassroots ? `${r.pos.grassroots} 年` : '无限制') },
  { label: '应届限制', get: (r) => (r.pos.rr.freshOnly ? (r.pos.rr.gradYear ? `限${r.pos.rr.gradYear}届` : '限应届') : '不限') },
  { label: '面试比例', get: (r) => r.pos.interviewRatio || '—' },
  { label: '备注', get: (r) => r.pos.remark || '—' },
  {
    label: '需要注意',
    get: (r) =>
      r.result.reasons
        .filter((x) => x.level !== 'pass')
        .map((x) => `${x.field}:${x.text}`)
        .join('\n') || '—',
  },
]
</script>

<template>
  <div class="page">
    <div class="top rise">
      <div>
        <div class="eyebrow">收藏与对比</div>
        <h1 class="page-title">我关注的岗位</h1>
        <div class="muted">收藏只保存在本机浏览器。勾选 2 到 5 个职位可横向对比。</div>
      </div>
      <el-button type="primary" :disabled="selected.length < 2" @click="openCompare">对比选中({{ selected.length }})</el-button>
    </div>

    <el-alert v-if="otherExam > 0" type="info" show-icon :closable="false" style="margin-bottom: 12px"
      :title="`另有 ${otherExam} 个收藏属于其他年度,切换右上角的考试年度即可查看。`" />

    <el-table :data="rows" class="paper-card fav-table rise" style="--i: 1" row-key="pos.id" @selection-change="onSelect" @row-click="openRow">
      <el-table-column type="selection" width="46" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }"><StatusTag :status="row.result.status" size="sm" /></template>
      </el-table-column>
      <el-table-column label="部门 / 职位" min-width="260">
        <template #default="{ row }">
          <div class="muted">{{ row.pos.org }}</div>
          <div class="serif" style="font-weight: 700; font-size: 15px">{{ row.pos.title }}</div>
        </template>
      </el-table-column>
      <el-table-column label="地点" prop="pos.location" width="150" />
      <el-table-column label="人数" prop="pos.headcount" width="64" align="center" />
      <el-table-column label="学历" prop="pos.eduText" width="130" />
      <el-table-column label="操作" width="90" align="center">
        <template #default="{ row }">
          <el-button link type="danger" @click.stop="favs.toggle(row.pos.id)">移除</el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="还没有收藏。在「匹配结果」里点击「收藏」即可加入。" /></template>
    </el-table>

    <el-dialog v-model="compareOpen" title="职位对比" width="92%" top="5vh">
      <el-table :data="lines" border>
        <el-table-column prop="label" label="项目" width="100" fixed />
        <el-table-column v-for="r in selected" :key="r.pos.id" :label="r.pos.org" min-width="220">
          <template #default="{ row: line }">
            <template v-if="line.label === '职位'">
              <StatusTag :status="r.result.status" style="margin-right: 6px" />{{ line.get(r) }}
            </template>
            <div v-else class="pre-wrap cell">{{ line.get(r) }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <PositionDrawer v-model="drawerOpen" :row="current" />
  </div>
</template>

<style scoped>
.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
  gap: 12px;
}
.fav-table {
  overflow: hidden;
}
.cell {
  font-size: 13px;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
