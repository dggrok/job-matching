import { ageBounds, formatYm } from './age'
import type { Catalog } from './catalog'
import { matchMajor, userLevel } from './major'
import type {
  ExamMeta,
  MajorRule,
  MatchResult,
  Position,
  Profile,
  Reason,
  ReasonLevel,
  Status,
} from './types'

/** 服务基层项目的标识与展示名(与 data-pipeline 的 PROJECT_KEYS 对应)。 */
export const PROJECT_LABELS: Record<string, string> = {
  village: '大学生村官',
  teacher: '农村义务教育阶段学校教师特设岗位计划',
  sanzhi: '“三支一扶”计划',
  west: '大学生志愿服务西部计划',
  veteran: '在军队服役5年(含)以上的高校毕业生退役士兵',
}

export interface MatchContext {
  profile: Profile
  exam: ExamMeta
  catalog: Catalog
  majorRules: Record<string, MajorRule>
}

const EDU_ORDER = ['大专', '本科', '硕士', '博士'] as const

function eduRank(e: string): number {
  return EDU_ORDER.indexOf(e as (typeof EDU_ORDER)[number])
}

/**
 * 判断一个用户能否报考一个职位。
 *
 * 三态:
 * - ok    所有硬条件都确定满足;
 * - maybe 没有确定不满足的条件,但有条件无法自动判定(备注里的限定、目录外专业名称、信息缺失),需人工核对;
 * - no    至少一个硬条件确定不满足。
 *
 * 原则:宁可标"待确认",也不把可能不能报的职位标成"符合"。
 */
export function matchPosition(pos: Position, ctx: MatchContext): MatchResult {
  const { profile, exam, catalog } = ctx
  const reasons: Reason[] = []
  const add = (level: ReasonLevel, field: string, text: string) => reasons.push({ level, field, text })

  // ---- 学历 ----
  if (pos.edu.length === 0) {
    add('warn', '学历', `学历要求无法识别(${pos.eduText}),请核对`)
  } else if (!profile.highestEdu) {
    add('warn', '学历', `要求「${pos.eduText}」,你尚未填写最高学历`)
  } else if (pos.edu.includes(profile.highestEdu)) {
    add('pass', '学历', `要求「${pos.eduText}」,你的最高学历为${profile.highestEdu}`)
  } else {
    add('fail', '学历', `要求「${pos.eduText}」,你的最高学历为${profile.highestEdu},不符合(须以最高学历报考)`)
  }

  // ---- 学位 ----
  switch (pos.degree) {
    case 'none':
      add('pass', '学位', '学位无要求')
      break
    case 'matchHighest':
    case 'bachelor':
    case 'master':
    case 'doctor': {
      const needRank = { matchHighest: 0, bachelor: 1, master: 2, doctor: 3 }[pos.degree]
      if (profile.hasDegree === null) {
        add('warn', '学位', '要求具有相应学位,你尚未填写是否取得学位')
      } else if (!profile.hasDegree) {
        add('fail', '学位', '要求具有与最高学历相对应的学位,你尚未取得')
      } else if (pos.degree !== 'matchHighest' && !profile.highestEdu) {
        add('warn', '学位', '学位有层次要求,你尚未填写最高学历,无法判断')
      } else if (pos.degree !== 'matchHighest' && eduRank(profile.highestEdu) < needRank) {
        add('fail', '学位', '学位层次不满足要求')
      } else {
        add('pass', '学位', '学位满足要求')
      }
      break
    }
    default:
      add('warn', '学位', '学位要求无法识别,请核对')
  }

  // ---- 政治面貌 ----
  if (pos.political === 'any') {
    add('pass', '政治面貌', '政治面貌不限')
  } else if (pos.political === 'party') {
    if (profile.political === 'party') add('pass', '政治面貌', '要求中共党员')
    else if (profile.political === 'prospective')
      add('pass', '政治面貌', '要求中共党员,预备党员可报考')
    else if (profile.political === 'unknown') add('warn', '政治面貌', '要求中共党员,你尚未填写政治面貌')
    else add('fail', '政治面貌', '要求中共党员')
  } else if (pos.political === 'partyOrLeague') {
    if (profile.political === 'unknown') add('warn', '政治面貌', '要求中共党员或共青团员,你尚未填写政治面貌')
    else if (profile.political === 'masses') add('fail', '政治面貌', '要求中共党员或共青团员')
    else add('pass', '政治面貌', '要求中共党员或共青团员')
  } else {
    add('warn', '政治面貌', '政治面貌要求无法识别,请核对')
  }

  // ---- 基层工作经历 ----
  matchGrassroots(pos, profile, add)

  // ---- 应届 / 往届 ----
  matchFresh(pos, profile, exam, add)

  // ---- 性别 ----
  if (pos.rr.gender) {
    const label = pos.rr.gender === 'male' ? '男性' : '女性'
    if (!profile.gender) add('warn', '性别', `限${label},你尚未填写性别`)
    else if (profile.gender === pos.rr.gender) add('pass', '性别', `限${label}`)
    else add('fail', '性别', `限${label},不符合`)
  }

  // ---- 年龄 ----
  matchAge(pos, profile, exam, add)

  // ---- 专业 ----
  const rule = ctx.majorRules[pos.majorId]
  if (rule) {
    const v = matchMajor(rule, pos, profile, catalog)
    add(v.level, '专业', v.text)
  } else {
    add('warn', '专业', '缺少专业规则,请核对')
  }

  // ---- 英语 ----
  matchEnglish(pos, profile, add)

  // ---- 法律职业资格、其他证书 ----
  if (pos.rr.legalQualification) {
    if (profile.legalQualification) add('pass', '资格证书', '要求法律职业资格证书,你已具备')
    else add('fail', '资格证书', '要求法律职业资格证书,你尚未取得')
  }
  const otherCerts = (pos.rr.certificates ?? []).filter(
    (t) => !(profile.legalQualification && t.includes('法律职业资格')) && !(pos.rr.legalQualification && t.includes('法律职业资格')),
  )
  for (const t of otherCerts) add('warn', '资格证书', `备注要求:${t},请自行核对`)

  // ---- 户籍 / 生源 ----
  for (const t of pos.rr.residency ?? []) {
    if (profile.originProvince && t.includes(profile.originProvince)) {
      add('pass', '户籍/生源', `备注:${t}(与你填写的地区相符,请仍以原文为准)`)
    } else {
      add('warn', '户籍/生源', `备注:${t},请核对你的户籍或生源地`)
    }
  }

  // ---- 工作经历(通常针对非应届) ----
  if (profile.freshStatus === 'none') {
    for (const t of pos.rr.workExperience ?? []) add('warn', '工作经历', `备注:${t}`)
  }

  // ---- 研究生须同时具备本科与研究生学历学位 ----
  if (pos.rr.needAllStageDegrees && userLevel(profile) === 'PG') {
    add('warn', '学历阶段', '备注要求各学历阶段均取得相应学历和学位,请确认本科阶段也满足')
  }

  return { status: aggregate(reasons), reasons }
}

function aggregate(reasons: Reason[]): Status {
  if (reasons.some((r) => r.level === 'fail')) return 'no'
  if (reasons.some((r) => r.level === 'warn')) return 'maybe'
  return 'ok'
}

type Add = (level: ReasonLevel, field: string, text: string) => void

function matchGrassroots(pos: Position, profile: Profile, add: Add): void {
  const need = pos.grassroots
  const projects = pos.projects
  if (projects.length > 0) {
    const names = projects.map((p) => PROJECT_LABELS[p] ?? p).join('、')
    const hit = projects.some((p) => profile.projects.includes(p))
    if (hit) {
      add('pass', '基层经历', `限服务基层项目人员(${names}),你具备所列项目经历`)
    } else if (need > 0 && profile.grassrootsYears >= need) {
      // 口径:项目限定与年限是否可以互相替代,以招考简章和报考指南为准
      add('warn', '基层经历', `职位限定服务基层项目(${names}),你有 ${profile.grassrootsYears} 年基层工作经历但未选择所列项目,请核对报考指南`)
    } else {
      add('fail', '基层经历', `限服务基层项目人员(${names}),你不具备`)
    }
    return
  }
  if (need === 0) {
    add('pass', '基层经历', '无基层工作经历要求')
  } else if (profile.grassrootsYears >= need) {
    add('pass', '基层经历', `要求 ${need} 年以上基层工作经历,你有 ${profile.grassrootsYears} 年`)
  } else {
    add('fail', '基层经历', `要求 ${need} 年以上基层工作经历,你只有 ${profile.grassrootsYears} 年`)
  }
}

function matchFresh(pos: Position, profile: Profile, exam: ExamMeta, add: Add): void {
  if (!pos.rr.freshOnly) {
    add('pass', '应届/往届', '不限应届')
    return
  }
  const year = pos.rr.gradYear
  const label = year ? `限${year}届高校毕业生` : '限应届高校毕业生'
  if (profile.freshStatus === 'unknown') {
    add('warn', '应届/往届', `${label},你尚未填写应届状态`)
  } else if (profile.freshStatus === 'none') {
    add('fail', '应届/往届', `${label},你不是应届毕业生`)
  } else if (profile.freshStatus === 'reserved') {
    if (year) add('fail', '应届/往届', `${label},往届生不符合`)
    else add('warn', '应届/往届', `${label};择业期内未就业的往届生可按应届对待,需满足户口档案要求,请核对`)
  } else if (year && year !== exam.graduateYear) {
    add('warn', '应届/往届', `${label},与本年度应届届别(${exam.graduateYear})不一致,请核对`)
  } else {
    add('pass', '应届/往届', label)
  }
}

function matchAge(pos: Position, profile: Profile, exam: ExamMeta, add: Add): void {
  const rule = exam.ageRule
  if (!rule) {
    add('warn', '年龄', '缺少年龄规则,请以公告为准')
    return
  }
  if (!profile.birth) {
    add('warn', '年龄', '尚未填写出生年月,无法判断年龄是否符合')
    return
  }
  const freshPg =
    profile.freshStatus === 'current' && (profile.highestEdu === '硕士' || profile.highestEdu === '博士')
  const b = ageBounds(rule, pos, freshPg)
  const desc = `要求 ${formatYm(b.oldest)} 至 ${formatYm(b.youngest)} 期间出生`
  if (profile.birth > b.youngest) {
    add('fail', '年龄', `${desc},你未满 ${rule.minAge} 周岁`)
  } else if (profile.birth >= b.oldest) {
    add('pass', '年龄', desc)
  } else if (b.relaxedOldest && profile.birth >= b.relaxedOldest) {
    add('warn', '年龄', `${desc};备注称特定条件下可放宽到 ${formatYm(b.relaxedOldest)} 以后出生,请核对是否符合`)
  } else {
    add('fail', '年龄', `${desc},你超过年龄上限`)
  }
}

function matchEnglish(pos: Position, profile: Profile, add: Add): void {
  const cet = pos.rr.cet
  if (!cet) return
  const lvl = userLevel(profile)
  const need = (lvl === 'UG' ? cet.UG : cet.PG) ?? cet.ANY
  if (!need) return
  const label = need === 4 ? '大学英语四级(425分)' : '大学英语六级(425分)'
  const have = profile.cet === '6' ? 6 : profile.cet === '4' ? 4 : profile.cet === 'none' ? 0 : -1
  if (have < 0) {
    add('warn', '英语', `要求${label},你尚未填写英语等级`)
  } else if (have >= need) {
    add('pass', '英语', `要求${label},你已达到`)
  } else if (pos.rr.cetAltAllowed && profile.hasAltEnglishCert) {
    add('pass', '英语', `要求${label},你以雅思/托福/英语专业等级替代(请以备注为准)`)
  } else {
    add('fail', '英语', `要求${label},你未达到`)
  }
}
