/**
 * 数据契约与匹配引擎的类型定义。
 * 与 data-pipeline 的输出保持一致,字段含义见方案文档「B. 数据契约」。
 */

export type EduLevel = '大专' | '本科' | '硕士' | '博士'

export interface QualifierExclude {
  kind: 'exclude'
  text: string
  refs: string[]
}
export interface QualifierRestrict {
  kind: 'restrict'
  text: string
}
export type Qualifier = QualifierExclude | QualifierRestrict

export interface MajorToken {
  raw: string
  name: string
  codes: string[]
  refs: string[]
  partial: boolean
  resolved: boolean
  qualifiers: Qualifier[]
  likelyLevel?: 'UG' | 'PG'
}

export interface MajorSegment {
  level: 'UG' | 'PG' | 'ANY'
  tokens: MajorToken[]
}

export interface MajorRule {
  text: string
  unlimited: boolean
  segments: MajorSegment[]
  warnings: string[]
}

export interface RemarkRules {
  freshOnly?: boolean
  gradYear?: number
  gender?: 'male' | 'female'
  maxAge?: number
  ageRelaxedTo?: number
  cet?: { UG?: number; PG?: number; ANY?: number }
  cetAltAllowed?: boolean
  residency?: string[]
  certificates?: string[]
  legalQualification?: boolean
  workExperience?: string[]
  minServiceYears?: number
  majorAnyLevel?: boolean
  needAllStageDegrees?: boolean
}

export interface Position {
  id: string
  code: string
  deptCode: string
  org: string
  unit: string
  orgType: string
  orgLevel: string
  title: string
  examCategory: string
  attr: string
  dist: string
  intro: string
  headcount: number
  location: string
  hukou: string
  edu: EduLevel[]
  eduText: string
  degree: 'matchHighest' | 'bachelor' | 'master' | 'doctor' | 'none' | 'unknown'
  political: 'any' | 'party' | 'partyOrLeague' | 'unknown'
  grassroots: number
  projects: string[]
  majorId: string
  remark: string
  rr: RemarkRules
  interviewRatio: string
  skillTest: string
  site: string
  phones: string[]
  sheet: string
  police?: boolean
  warnings?: string[]
}

export interface AgeRule {
  refYear: number
  refMonth: number
  minAge: number
  maxAge: number
  maxAgeFreshPg: number
  policeMaxAge: number
  policeMaxAgeFreshPg: number
  note?: string
}

export interface ExamMeta {
  id: string
  name: string
  type: string
  year: number
  graduateYear: number
  publishedAt?: string
  signup?: string
  writtenExam?: string
  source: string
  sample?: boolean
  pending: boolean
  positions?: number
  headcount?: number
  ageRule?: AgeRule
  dataVersion?: string
  file: string | null
}

export interface Manifest {
  exams: ExamMeta[]
  generatedAt?: string
}

export interface ExamData {
  examId: string
  majorRules: Record<string, MajorRule>
  positions: Position[]
}

/** catalog.json 中的节点:[id, 名称, 类型, 父级, 备注] */
export type CatalogRow = [string, string, string, string | null, string | null]
export interface CatalogFile {
  UG: CatalogRow[]
  PG: CatalogRow[]
  meta: { UG: string; PG: string }
}

// ---------------- 用户画像 ----------------

export type FreshStatus = 'none' | 'current' | 'reserved'
export type PoliticalStatus = 'party' | 'prospective' | 'league' | 'masses'
export type CetLevel = 'unknown' | 'none' | '4' | '6'

export interface Profile {
  highestEdu: EduLevel
  /** 是否已取得(或将取得)与最高学历对应的学位 */
  hasDegree: boolean
  ugMajorId: string | null
  pgMajorId: string | null
  /** 应届状态:none 非应届;current 当年届毕业生;reserved 择业期内未就业的往届生(视同应届) */
  freshStatus: FreshStatus
  /** 出生年月 YYYY-MM */
  birth: string
  gender: '' | 'male' | 'female'
  political: PoliticalStatus
  grassrootsYears: number
  projects: string[]
  cet: CetLevel
  hasAltEnglishCert: boolean
  legalQualification: boolean
  originProvince: string
}

// ---------------- 匹配结果 ----------------

export type Status = 'ok' | 'maybe' | 'no'
export type ReasonLevel = 'pass' | 'warn' | 'fail'

export interface Reason {
  level: ReasonLevel
  field: string
  text: string
}

export interface MatchResult {
  status: Status
  reasons: Reason[]
}
