<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNarrow } from '@/composables/useNarrow'
import { formatYm, ym } from '@/engine/age'
import { PROJECT_LABELS } from '@/engine/match'
import { useDataStore } from '@/stores/data'
import { useMatchStore } from '@/stores/match'
import { useProfileStore } from '@/stores/profile'

const router = useRouter()
const data = useDataStore()
const store = useProfileStore()
const match = useMatchStore()
const narrow = useNarrow(720)
const p = store.profile

const ugTree = computed(() => data.catalog?.tree('UG') ?? [])
const pgTree = computed(() => data.catalog?.tree('PG') ?? [])
const cascaderProps = { value: 'id', label: 'name', children: 'children', emitPath: false, expandTrigger: 'hover' as const }

const gradYear = computed(() => data.exam?.graduateYear ?? new Date().getFullYear())

const PROVINCES = [
  '北京', '天津', '上海', '重庆', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东',
  '河南', '湖北', '湖南', '广东', '广西', '海南', '四川', '贵州', '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆',
]

/** 当前考试口径下"一般报考者"的出生年月范围,给用户一个直观参照。 */
const generalRange = computed(() => {
  const r = data.exam?.ageRule
  if (!r) return ''
  return `${formatYm(ym(r.refYear - r.maxAge - 1, r.refMonth))} 至 ${formatYm(ym(r.refYear - r.minAge, r.refMonth))}`
})

const majorNote = computed(() => {
  const id = store.level === 'UG' ? p.ugMajorId : p.pgMajorId
  const n = id ? data.catalog?.get(id) : null
  return n?.note ?? ''
})

const summary = computed(() => match.summary)

function goResults() {
  router.push('/results')
}
</script>

<template>
  <div class="page">
    <header class="head rise">
      <div class="eyebrow">我的条件</div>
      <h1 class="page-title">告诉我你的情况</h1>
      <p class="muted">填得越完整,结果越准确。信息只保存在本机浏览器,不会上传。</p>
    </header>

    <el-alert
      v-if="store.missing.length"
      type="warning"
      show-icon
      :closable="false"
      class="notice rise"
      style="--i: 1"
      :title="`还需要填写:${store.missing.join('、')}`"
      description="缺少这些信息时,相关条件会被标为「待确认」,结果不够准确。"
    />

    <el-form :label-width="narrow ? 'auto' : '130px'" :label-position="narrow ? 'top' : 'right'" class="form">
      <section class="block paper-card rise" style="--i: 1">
        <h2 class="block-title"><span class="no">壹</span>学历与专业</h2>
        <el-form-item label="最高学历">
          <el-radio-group v-model="p.highestEdu">
            <el-radio-button value="大专">大专</el-radio-button>
            <el-radio-button value="本科">本科</el-radio-button>
            <el-radio-button value="硕士">硕士研究生</el-radio-button>
            <el-radio-button value="博士">博士研究生</el-radio-button>
          </el-radio-group>
          <div class="muted hint">须以已取得的最高学历报考;应届生以即将取得的最高学历报考。</div>
        </el-form-item>
        <el-form-item label="已取得对应学位">
          <el-radio-group v-model="p.hasDegree">
            <el-radio-button :value="true">已取得或将取得</el-radio-button>
            <el-radio-button :value="false">没有学位</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="本科专业">
          <el-cascader
            v-model="p.ugMajorId"
            :options="ugTree"
            :props="cascaderProps"
            filterable
            clearable
            placeholder="搜索或选择你的本科专业"
            class="wide"
          />
          <div v-if="store.level === 'UG' && majorNote" class="muted hint">目录注:{{ majorNote }}</div>
          <div class="muted hint">按《普通高等学校本科专业目录(2025年)》选择,与毕业证书上的专业保持一致。</div>
        </el-form-item>
        <el-form-item v-if="store.level === 'PG'" label="研究生专业">
          <el-cascader
            v-model="p.pgMajorId"
            :options="pgTree"
            :props="cascaderProps"
            filterable
            clearable
            placeholder="搜索或选择一级学科或专业学位类别"
            class="wide"
          />
          <div class="muted hint">按《研究生教育学科专业目录(2022年)》选择一级学科。职位若写到二级学科,会被标为「待确认」。</div>
        </el-form-item>
      </section>

      <section class="block paper-card rise" style="--i: 2">
        <h2 class="block-title"><span class="no">贰</span>身份与年龄</h2>
        <el-form-item label="应届状态">
          <el-radio-group v-model="p.freshStatus">
            <el-radio-button value="none">非应届(往届/社会人员)</el-radio-button>
            <el-radio-button value="current">{{ gradYear }}届应届毕业生</el-radio-button>
            <el-radio-button value="reserved">择业期内未就业的往届生</el-radio-button>
          </el-radio-group>
          <div class="muted hint">
            约三分之二的国考职位限应届毕业生。择业期(毕业后两年)内未落实工作、档案户口仍在学校或人才机构的往届生,可按应届对待,但限「{{ gradYear }}届」的职位不适用。
          </div>
        </el-form-item>
        <el-form-item label="出生年月" required>
          <el-date-picker v-model="p.birth" type="month" value-format="YYYY-MM" format="YYYY年M月" placeholder="选择出生年月" :clearable="false" />
          <div class="muted hint">
            年龄按公告的"出生年月区间"精确到月判断。<template v-if="generalRange">本年度口径下一般报考者需在 {{ generalRange }} 期间出生。</template>
          </div>
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="p.gender">
            <el-radio-button value="male">男</el-radio-button>
            <el-radio-button value="female">女</el-radio-button>
            <el-radio-button value="">不填</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="政治面貌">
          <el-radio-group v-model="p.political">
            <el-radio-button value="party">中共党员</el-radio-button>
            <el-radio-button value="prospective">中共预备党员</el-radio-button>
            <el-radio-button value="league">共青团员</el-radio-button>
            <el-radio-button value="masses">群众/其他</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </section>

      <section class="block paper-card rise" style="--i: 3">
        <h2 class="block-title"><span class="no">叁</span>经历、语言与证书</h2>
        <el-form-item label="基层工作年限">
          <el-input-number v-model="p.grassrootsYears" :min="0" :max="30" />
          <span class="muted" style="margin-left: 8px">年(签订劳动合同并缴纳社保的基层工作,可累计)</span>
        </el-form-item>
        <el-form-item label="服务基层项目">
          <el-checkbox-group v-model="p.projects">
            <el-checkbox v-for="(label, key) in PROJECT_LABELS" :key="key" :value="key" :label="label" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="大学英语等级">
          <el-radio-group v-model="p.cet">
            <el-radio-button value="unknown">不填</el-radio-button>
            <el-radio-button value="none">未通过四级</el-radio-button>
            <el-radio-button value="4">四级(425分以上)</el-radio-button>
            <el-radio-button value="6">六级(425分以上)</el-radio-button>
          </el-radio-group>
          <div style="margin-top: 8px; width: 100%">
            <el-checkbox v-model="p.hasAltEnglishCert" label="有雅思/托福/英语专业四八级成绩(部分职位可替代)" />
          </div>
        </el-form-item>
        <el-form-item label="法律职业资格证">
          <el-switch v-model="p.legalQualification" active-text="已取得" inactive-text="没有" />
        </el-form-item>
        <el-form-item label="户籍/生源地">
          <el-select v-model="p.originProvince" filterable clearable placeholder="用于核对限户籍或生源的职位" style="width: 260px">
            <el-option v-for="n in PROVINCES" :key="n" :label="n" :value="n" />
          </el-select>
        </el-form-item>
      </section>
    </el-form>

    <!-- 吸底结果栏:改条件时实时看到结果数 -->
    <div class="dock">
      <div class="dock-info">
        <span class="lead">按当前条件</span>
        <span class="n ok">{{ summary.ok }}</span><span class="t">个符合</span>
        <span class="n maybe">{{ summary.maybe }}</span><span class="t">个待确认</span>
        <span class="t hc">共可报 {{ summary.okHeadcount }} 人</span>
      </div>
      <div class="dock-ops">
        <el-button @click="store.reset">恢复默认</el-button>
        <el-button type="primary" @click="goResults">查看匹配结果</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 20px;
}
.head p {
  margin: 0;
}
.notice {
  margin-bottom: 16px;
}
.block {
  padding: 22px 28px 12px;
  margin-bottom: 18px;
}
.block-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.block-title .no {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  background: var(--seal);
  color: #fff;
  font-size: 16px;
  border-radius: 3px;
  letter-spacing: 0;
  transform: rotate(-4deg);
}
.hint {
  display: block;
  width: 100%;
  margin-top: 4px;
  line-height: 1.6;
}
.wide {
  width: 440px;
  max-width: 100%;
}

.dock {
  position: sticky;
  bottom: 16px;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  padding: 14px 20px;
  background: rgba(255, 253, 247, 0.96);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line-strong);
  border-top: 3px solid var(--navy);
  border-radius: var(--radius);
  box-shadow: 0 16px 36px -14px rgba(31, 58, 95, 0.45);
}
.dock-info {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 6px;
}
.dock-info .lead {
  margin-right: 8px;
  color: var(--ink-3);
  font-size: 13px;
}
.dock-info .n {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}
.dock-info .n.ok {
  color: var(--ok);
}
.dock-info .n.maybe {
  color: var(--maybe);
  margin-left: 10px;
}
.dock-info .t {
  font-size: 13px;
  color: var(--ink-2);
}
.dock-info .hc {
  margin-left: 14px;
  color: var(--ink-3);
}
.dock-ops {
  display: flex;
  gap: 8px;
  flex: none;
}

@media (max-width: 720px) {
  .block {
    padding: 18px 16px 8px;
  }
  .dock {
    flex-direction: column;
    align-items: stretch;
    bottom: 8px;
    padding: 10px 14px;
  }
  .dock-ops {
    justify-content: flex-end;
  }
  .dock-info .hc {
    display: none;
  }
}
</style>
