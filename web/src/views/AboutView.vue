<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from '@/components/StatusTag.vue'
import { useDataStore } from '@/stores/data'

const data = useDataStore()
const exam = computed(() => data.exam)
const pending = computed(() => data.exams.filter((e) => e.pending))
</script>

<template>
  <div class="page">
    <header class="head rise">
      <div class="eyebrow">数据说明</div>
      <h1 class="page-title">数据从哪里来,结果怎么看</h1>
    </header>

    <el-card v-if="exam" shadow="never" class="card">
      <template #header><span class="section-title">当前数据:{{ exam.name }}</span></template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="职位数 / 招考人数">{{ exam.positions }} 个 / {{ exam.headcount }} 人</el-descriptions-item>
        <el-descriptions-item label="数据版本">{{ exam.dataVersion }}</el-descriptions-item>
        <el-descriptions-item label="公告发布">{{ exam.publishedAt || '—' }}</el-descriptions-item>
        <el-descriptions-item label="报名时间">{{ exam.signup || '—' }}</el-descriptions-item>
        <el-descriptions-item label="笔试时间">{{ exam.writtenExam || '—' }}</el-descriptions-item>
        <el-descriptions-item label="数据生成时间">{{ data.manifest?.generatedAt || '—' }}</el-descriptions-item>
        <el-descriptions-item label="官方来源" :span="2">
          <a :href="exam.source" target="_blank" rel="noopener">{{ exam.source }}</a>
        </el-descriptions-item>
        <el-descriptions-item label="年龄口径(公告级)" :span="2">{{ exam.ageRule?.note }}</el-descriptions-item>
      </el-descriptions>
      <el-alert
        v-if="exam.sample"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 12px"
        title="这是开发样本"
        description="2026 年度职位表用于开发和验证。2027 年度职位表发布后,按 README 的流程导入并核对当年公告,数据才能用于实际报名决策。"
      />
      <div v-for="e in pending" :key="e.id" class="muted" style="margin-top: 10px">
        {{ e.name }}:尚未发布(预计 2026-10-14),官方入口
        <a :href="e.source" target="_blank" rel="noopener">{{ e.source }}</a>
      </div>
    </el-card>

    <el-card shadow="never" class="card">
      <template #header><span class="section-title">匹配结果怎么看</span></template>
      <p class="row"><StatusTag status="ok" size="sm" /><span>学历、学位、政治面貌、基层经历、应届、性别、年龄、专业、英语等条件都能明确判断为满足。</span></p>
      <p class="row"><StatusTag status="maybe" size="sm" /><span>没有明确不满足的条件,但有条件系统无法自动判定,例如备注里的户籍或证书要求、专业写到二级学科或带附加限定、目录外的专业名称、你没有填写的信息。请打开详情核对原文。</span></p>
      <p class="row"><StatusTag status="no" size="sm" /><span>至少有一项条件明确不满足,详情里会列出全部原因。</span></p>
      <p class="muted">原则是宁可标「待确认」,也不把可能不能报的职位标成「符合」。</p>
    </el-card>

    <el-card shadow="never" class="card">
      <template #header><span class="section-title">已知局限</span></template>
      <ol class="limits">
        <li>「专业」「备注」是自由文本,系统只抽取常见、明确的条件。体能、视力、专业能力测试、工作经历细则等仍需阅读备注原文。</li>
        <li>研究生二级学科不在 2022 版目录里,职位写到二级学科时只能按一级学科匹配并标为待确认。</li>
        <li>招录机关自定义的专业大类(如「财会审计类」)按名称推断映射,同样标为待确认。</li>
        <li>「基层工作年限」与「服务基层项目」两个字段的互相关系,请对照当年《报考指南》核实。</li>
        <li>年龄按公告的出生年月区间判断。公安民警职位使用更严的年龄线;监狱、戒毒警察等特殊职位若备注未写明,可能与实际口径有差异。</li>
        <li>目前只覆盖国考,省考(浙江、江苏)在二期。</li>
      </ol>
    </el-card>

    <el-card shadow="never" class="card">
      <template #header><span class="section-title">专业目录</span></template>
      <div>{{ data.catalog?.meta.UG }}(教育部)</div>
      <div>{{ data.catalog?.meta.PG }}(国务院学位委员会、教育部)</div>
    </el-card>
  </div>
</template>

<style scoped>
.card {
  margin-bottom: 16px;
}
.limits {
  margin: 0;
  padding-left: 20px;
  line-height: 1.9;
}
p {
  line-height: 1.8;
  margin: 6px 0;
}
.head {
  margin-bottom: 20px;
}
.row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin: 12px 0;
}
.row :deep(.seal) {
  flex: none;
  margin-top: 3px;
  min-width: 56px;
  text-align: center;
}
</style>
