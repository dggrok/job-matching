<script setup lang="ts">
import { computed } from 'vue'
import { POLITICAL_LABEL, type Row } from '@/engine/filters'
import { PROJECT_LABELS } from '@/engine/match'
import type { ReasonLevel } from '@/engine/types'
import { useDataStore } from '@/stores/data'
import { useFavoritesStore } from '@/stores/favorites'
import StatusTag from './StatusTag.vue'

const props = defineProps<{ row: Row | null }>()
const visible = defineModel<boolean>({ required: true })

const data = useDataStore()
const favs = useFavoritesStore()

const pos = computed(() => props.row?.pos ?? null)
const majorText = computed(() => (pos.value ? data.examData?.majorRules[pos.value.majorId]?.text ?? '' : ''))

const LEVEL_META: Record<ReasonLevel, { label: string }> = {
  fail: { label: '不符合' },
  warn: { label: '待确认' },
  pass: { label: '符合' },
}

const groups = computed(() => {
  const reasons = props.row?.result.reasons ?? []
  return (['fail', 'warn', 'pass'] as ReasonLevel[])
    .map((level) => ({ level, items: reasons.filter((r) => r.level === level) }))
    .filter((g) => g.items.length)
})

const projects = computed(() => (pos.value?.projects ?? []).map((p) => PROJECT_LABELS[p] ?? p).join('、') || '无限制')
</script>

<template>
  <el-drawer v-model="visible" size="640px" :with-header="false" destroy-on-close>
    <template v-if="pos && row">
      <div class="head">
        <div>
          <div class="org">{{ pos.org }}</div>
          <div class="title">{{ pos.title }}</div>
          <div class="muted">
            {{ pos.unit }}<template v-if="pos.unit"> · </template>职位代码 {{ pos.code }} · 部门代码 {{ pos.deptCode }}
          </div>
        </div>
        <div class="actions">
          <StatusTag :status="row.result.status" size="lg" />
          <el-button size="small" :type="favs.has(pos.id) ? 'warning' : 'default'" @click="favs.toggle(pos.id)">
            {{ favs.has(pos.id) ? '已收藏' : '收藏' }}
          </el-button>
        </div>
      </div>

      <h4 class="section-title">匹配结果说明</h4>
      <div v-for="g in groups" :key="g.level" class="group" :class="g.level">
        <div class="group-head">{{ LEVEL_META[g.level].label }}({{ g.items.length }})</div>
        <div v-for="(r, i) in g.items" :key="i" class="reason">
          <span class="chip">{{ r.field }}</span>
          <span>{{ r.text }}</span>
        </div>
      </div>

      <h4 class="section-title" style="margin-top: 20px">职位信息</h4>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="招考人数">{{ pos.headcount }}</el-descriptions-item>
        <el-descriptions-item label="工作地点">{{ pos.location }}</el-descriptions-item>
        <el-descriptions-item label="机构性质">{{ pos.orgType }}</el-descriptions-item>
        <el-descriptions-item label="机构层级">{{ pos.orgLevel }}</el-descriptions-item>
        <el-descriptions-item label="考试类别">{{ pos.examCategory }}</el-descriptions-item>
        <el-descriptions-item label="职位属性">{{ pos.attr }}</el-descriptions-item>
        <el-descriptions-item label="职位分布">{{ pos.dist }}</el-descriptions-item>
        <el-descriptions-item label="落户地点">{{ pos.hukou || '—' }}</el-descriptions-item>
        <el-descriptions-item label="学历">{{ pos.eduText }}</el-descriptions-item>
        <el-descriptions-item label="政治面貌">{{ POLITICAL_LABEL[pos.political] ?? pos.political }}</el-descriptions-item>
        <el-descriptions-item label="基层工作最低年限">{{ pos.grassroots ? pos.grassroots + ' 年' : '无限制' }}</el-descriptions-item>
        <el-descriptions-item label="服务基层项目">{{ projects }}</el-descriptions-item>
        <el-descriptions-item label="面试人员比例">{{ pos.interviewRatio || '—' }}</el-descriptions-item>
        <el-descriptions-item label="专业能力测试">{{ pos.skillTest || '—' }}</el-descriptions-item>
        <el-descriptions-item label="专业要求(原文)" :span="2"><div class="pre-wrap">{{ majorText }}</div></el-descriptions-item>
        <el-descriptions-item label="职位简介" :span="2">{{ pos.intro || '—' }}</el-descriptions-item>
        <el-descriptions-item label="备注(原文)" :span="2"><div class="pre-wrap">{{ pos.remark || '—' }}</div></el-descriptions-item>
        <el-descriptions-item label="咨询电话" :span="2">{{ pos.phones.join(' / ') || '—' }}</el-descriptions-item>
        <el-descriptions-item label="部门网站" :span="2">
          <a v-if="pos.site && pos.site !== '无'" :href="pos.site.startsWith('http') ? pos.site : 'http://' + pos.site" target="_blank" rel="noopener">{{ pos.site }}</a>
          <span v-else>—</span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="muted" style="margin-top: 12px">「备注」里可能还有系统未解析的条件(体能、视力、工作经历等),报名前务必阅读原文。</div>
    </template>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.org {
  font-size: 13px;
  color: var(--ink-3);
}
.title {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.03em;
  line-height: 1.35;
  margin: 4px 0 6px;
}
.actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  flex: none;
}
.group {
  --c: var(--ok);
  --c-soft: var(--ok-soft);
  margin-bottom: 10px;
  padding: 10px 14px;
  border-left: 4px solid var(--c);
  background: var(--c-soft);
  border-radius: 0 3px 3px 0;
}
.group.warn {
  --c: var(--maybe);
  --c-soft: var(--maybe-soft);
}
.group.fail {
  --c: var(--seal);
  --c-soft: var(--seal-soft);
}
.group-head {
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.1em;
  color: var(--c);
  margin-bottom: 4px;
}
.reason {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 4px 0;
  line-height: 1.6;
  font-size: 14px;
}
.chip {
  flex: none;
  margin-top: 2px;
  min-width: 56px;
  text-align: center;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--c);
  border: 1px solid var(--c);
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.55);
}
</style>
