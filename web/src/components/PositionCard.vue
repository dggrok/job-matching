<script setup lang="ts">
import { computed } from 'vue'
import type { Row } from '@/engine/filters'
import StatusTag from './StatusTag.vue'

const props = defineProps<{ row: Row; majorText: string; fav: boolean }>()
const emit = defineEmits<{ open: []; toggleFav: [] }>()

const pos = computed(() => props.row.pos)
const status = computed(() => props.row.result.status)

/** 卡片上的关键限制标签,一眼看出最容易踩雷的条件 */
const flags = computed(() => {
  const list: { text: string; hot?: boolean }[] = []
  const rr = pos.value.rr
  if (rr.freshOnly) list.push({ text: rr.gradYear ? `限${rr.gradYear}届毕业生` : '限应届毕业生', hot: true })
  if (rr.gender) list.push({ text: rr.gender === 'male' ? '限男性' : '限女性', hot: true })
  if (pos.value.police) list.push({ text: '公安民警' })
  if (pos.value.political !== 'any' && pos.value.political !== 'unknown') {
    list.push({ text: pos.value.political === 'party' ? '限中共党员' : '党员或团员' })
  }
  if (pos.value.grassroots) list.push({ text: `基层${pos.value.grassroots}年` })
  return list
})

/** 不符合、待确认的原因:先列不符合,再列待确认,最多 3 条 */
const issues = computed(() => {
  const all = props.row.result.reasons.filter((r) => r.level !== 'pass')
  all.sort((a, b) => (a.level === b.level ? 0 : a.level === 'fail' ? -1 : 1))
  return { shown: all.slice(0, 3), more: Math.max(0, all.length - 3) }
})

const majorPass = computed(() => props.row.result.reasons.find((r) => r.field === '专业' && r.level === 'pass')?.text ?? '')
</script>

<template>
  <article class="card" :class="status" @click="emit('open')">
    <span class="rail" />
    <header class="top">
      <div class="org">
        {{ pos.org }}<template v-if="pos.unit"><i> / </i>{{ pos.unit }}</template>
      </div>
      <StatusTag :status="status" size="sm" />
    </header>

    <h3 class="title">{{ pos.title }}</h3>

    <div class="tags">
      <span class="tag strong">招 {{ pos.headcount }} 人</span>
      <span class="tag">{{ pos.location }}</span>
      <span class="tag">{{ pos.eduText }}</span>
      <span v-for="f in flags" :key="f.text" class="tag" :class="{ hot: f.hot }">{{ f.text }}</span>
    </div>

    <div class="major"><b>专业</b><span>{{ majorText }}</span></div>

    <ul v-if="status !== 'ok'" class="issues">
      <li v-for="(r, i) in issues.shown" :key="i" :class="r.level">
        <em>{{ r.level === 'fail' ? '×' : '?' }}</em>
        <span><b>{{ r.field }}</b>{{ r.text }}</span>
      </li>
      <li v-if="issues.more" class="more">另有 {{ issues.more }} 项,见详情</li>
    </ul>
    <div v-else class="allok">
      <em>✓</em><span>{{ majorPass || '所有条件均明确满足' }}</span>
    </div>

    <footer class="foot">
      <span class="code">{{ pos.sheet }} · {{ pos.code }}</span>
      <span class="ops">
        <button class="op" :class="{ on: fav }" type="button" @click.stop="emit('toggleFav')">{{ fav ? '★ 已收藏' : '☆ 收藏' }}</button>
        <button class="op primary" type="button" @click.stop="emit('open')">详情 →</button>
      </span>
    </footer>
  </article>
</template>

<style scoped>
.card {
  --c: var(--no);
  --c-soft: var(--no-soft);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 20px 14px 24px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.card.ok {
  --c: var(--ok);
  --c-soft: var(--ok-soft);
}
.card.maybe {
  --c: var(--maybe);
  --c-soft: var(--maybe-soft);
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lift);
  border-color: var(--line-strong);
}
.rail {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: var(--c);
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.org {
  font-size: 13px;
  color: var(--ink-3);
  line-height: 1.5;
  letter-spacing: 0.02em;
}
.org i {
  font-style: normal;
  color: var(--line-strong);
}
.title {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.03em;
  line-height: 1.4;
  color: var(--ink);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag {
  font-size: 12px;
  line-height: 1;
  padding: 5px 8px;
  color: var(--ink-2);
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 2px;
}
.tag.strong {
  color: var(--navy);
  border-color: var(--navy);
  background: transparent;
  font-weight: 600;
}
.tag.hot {
  color: var(--seal);
  background: var(--seal-soft);
  border-color: #e7bdb6;
}

.major {
  display: flex;
  gap: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ink-2);
}
.major b {
  flex: none;
  color: var(--ink-3);
  font-weight: 600;
  letter-spacing: 0.2em;
}
.major span {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.issues {
  list-style: none;
  margin: 0;
  padding: 10px 12px;
  background: var(--c-soft);
  border-radius: 3px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.issues li {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ink-2);
}
.issues li em {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  display: grid;
  place-items: center;
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  border-radius: 50%;
  background: var(--maybe);
}
.issues li.fail em {
  background: var(--seal);
}
.issues li b {
  margin-right: 6px;
  color: var(--ink);
}
.issues li.more {
  color: var(--ink-3);
  padding-left: 24px;
}
.issues li.more em {
  display: none;
}

.allok {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ok);
  background: var(--ok-soft);
  border-radius: 3px;
}
.allok em {
  flex: none;
  font-style: normal;
  font-weight: 700;
}

.foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px dashed var(--line-strong);
}
.code {
  font-size: 12px;
  color: var(--ink-3);
  letter-spacing: 0.02em;
}
.ops {
  display: flex;
  gap: 4px;
}
.op {
  font: inherit;
  font-size: 13px;
  padding: 4px 10px;
  color: var(--ink-2);
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.op:hover {
  background: var(--paper);
  color: var(--navy);
}
.op.on {
  color: var(--maybe);
}
.op.primary {
  color: var(--navy);
  font-weight: 600;
}
</style>
