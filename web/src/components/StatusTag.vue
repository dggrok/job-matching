<script setup lang="ts">
import type { Status } from '@/engine/types'

withDefaults(defineProps<{ status: Status; size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })

const LABEL: Record<Status, string> = { ok: '符合', maybe: '待确认', no: '不符合' }
</script>

<template>
  <span class="seal" :class="[status, size]">{{ LABEL[status] }}</span>
</template>

<style scoped>
/* 印章式状态标记:方框加粗边,宋体,略微倾斜 */
.seal {
  display: inline-block;
  font-family: var(--font-serif);
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: 1;
  border: 1.5px solid currentColor;
  border-radius: 3px;
  padding: 5px 7px 5px 9px;
  transform: rotate(-3deg);
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.4);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.6);
}
.sm {
  font-size: 12px;
  padding: 3px 4px 3px 6px;
}
.md {
  font-size: 14px;
}
.lg {
  font-size: 20px;
  padding: 8px 10px 8px 14px;
  border-width: 2px;
}
.ok {
  color: var(--ok);
}
.maybe {
  color: var(--maybe);
}
.no {
  color: var(--no);
}
</style>
