<script setup lang="ts">
import { onMounted } from 'vue'
import { useDataStore } from '@/stores/data'

const data = useDataStore()

onMounted(() => {
  data.init()
})

const NAV = [
  { to: '/results', label: '匹配结果' },
  { to: '/profile', label: '我的条件' },
  { to: '/favorites', label: '收藏与对比' },
  { to: '/about', label: '数据说明' },
]

async function onExamChange(id: string) {
  await data.selectExam(id)
}

/** 下拉里的考试短名称,避免整句机关名称撑宽顶栏。 */
function shortName(e: { name: string; year: number; kind?: string; province?: string | null; sample?: boolean }) {
  const base = e.kind === 'shengkao' ? `${e.year} 年度${e.province ?? ''}省考` : `${e.year} 年度国考`
  return e.sample ? `${base}(样本)` : base
}
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="header-inner">
        <router-link to="/results" class="brand">
          <span class="mark">考</span>
          <span class="brand-text">
            <span class="brand-name">考公职位匹配</span>
            <span class="brand-sub">按条件筛出能报的岗位</span>
          </span>
        </router-link>

        <nav class="nav">
          <router-link v-for="n in NAV" :key="n.to" :to="n.to" class="nav-link" active-class="active">{{ n.label }}</router-link>
        </nav>

        <el-select
          v-if="data.availableExams.length"
          :model-value="data.examId"
          class="exam"
          :loading="data.loading"
          @change="onExamChange"
        >
          <el-option v-for="e in data.availableExams" :key="e.id" :label="shortName(e)" :value="e.id" />
        </el-select>
      </div>
    </header>

    <main class="main">
      <div v-if="data.error" class="page">
        <el-alert type="error" show-icon :closable="false" title="数据加载失败">
          <template #default>
            {{ data.error }}。请先在 data-pipeline 目录运行 <code>.venv/bin/python -m src.build --all</code> 生成数据。
          </template>
        </el-alert>
      </div>
      <div v-else-if="!data.examData" v-loading="true" class="loading" :element-loading-text="data.stage || '加载中…'" />
      <router-view v-else />
    </main>

    <footer class="footer">
      <span class="rule" />
      <p>结果仅供参考,最终以官方公告和招录机关确认为准。</p>
      <p>你的条件只保存在本机浏览器中,不会上传。</p>
    </footer>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 253, 247, 0.92);
  backdrop-filter: blur(8px);
  border-top: 3px solid var(--seal);
  border-bottom: 1px solid var(--line-strong);
}
.header-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  min-height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--ink);
  flex: none;
}
.mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  background: var(--seal);
  color: #fff;
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 22px;
  border-radius: 3px;
  transform: rotate(-4deg);
  box-shadow: 0 0 0 2px var(--card), 0 0 0 3px var(--seal);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.brand-name {
  font-family: var(--font-serif);
  font-weight: 700;
  font-size: 19px;
  letter-spacing: 0.08em;
}
.brand-sub {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--ink-3);
  margin-top: 2px;
}

.nav {
  display: flex;
  gap: 4px;
  flex: 1;
}
.nav-link {
  position: relative;
  padding: 22px 14px;
  font-size: 15px;
  letter-spacing: 0.06em;
  color: var(--ink-2);
  text-decoration: none;
  transition: color 0.2s;
}
.nav-link::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 3px;
  background: var(--navy);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.25s ease;
}
.nav-link:hover {
  color: var(--navy);
}
.nav-link.active {
  color: var(--navy);
  font-weight: 600;
}
.nav-link.active::after {
  transform: scaleX(1);
}

.exam {
  width: 190px;
  flex: none;
}

.main {
  flex: 1;
}
.loading {
  height: 60vh;
}

.footer {
  text-align: center;
  color: var(--ink-3);
  font-size: 12px;
  letter-spacing: 0.06em;
  padding: 8px 16px 36px;
}
.footer p {
  margin: 2px 0;
}
.rule {
  display: block;
  width: 64px;
  height: 2px;
  margin: 0 auto 14px;
  background: var(--seal);
  opacity: 0.6;
}

@media (max-width: 860px) {
  .header-inner {
    flex-wrap: wrap;
    gap: 0 12px;
    padding: 8px 14px 0;
    min-height: 0;
  }
  .brand {
    order: 1;
    margin-bottom: 8px;
  }
  .brand-sub {
    display: none;
  }
  .exam {
    order: 2;
    margin-left: auto;
    margin-bottom: 8px;
    width: 160px;
  }
  .nav {
    order: 3;
    flex-basis: 100%;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .nav-link {
    padding: 10px 12px;
    white-space: nowrap;
  }
  .nav-link::after {
    left: 12px;
    right: 12px;
  }
}
</style>
