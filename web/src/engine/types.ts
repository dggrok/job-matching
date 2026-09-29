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
  /** 江苏等省的自定义「专业大类」引用:实际的目录节点集合在 ExamData.catRefs 里 */
  cat?: string
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
  // ---- 以下字段主要用于省考 ----
  /** 需要人工核对的其他硬条件原句(英语要求、特殊证明材料等),一律待确认 */
  notes?: string[]
  /** 特定身份限制(优秀村干部、退役军人、残疾人、少数民族等),系统无法判断,一律待确认 */
  identity?: string[]
  /** 仅对以研究生学历报考者有效的「本科阶段」要求 */
  ugStage?: string[]
  /** 应届类职位同时开放给哪些非应届人员(不满足应届时不判不符合,改为待确认) */
  freshAlt?: string
  /** 服务基层项目之外还允许的其他身份(如乡镇事业编制人员),没有所列项目时不判不符合 */
  altIdentity?: string
  /** 年龄按专门规定执行(公安、司法警察等),公告级年龄线只能作参考:通过时也只显示待确认 */
  ageSpecial?: boolean
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
  /** 该职位自己的年龄线(周岁);省考每个职位的年龄上限可能不同,缺省时用考试的公告级 ageRule */
  ageMin?: number
  ageMax?: number
  ageMaxFresh?: number
  /** 详情里额外展示的 [名称, 内容] */
  extras?: [string, string][]
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
  /** guokao | shengkao */
  kind?: string
  /** 省考所属省份,如「浙江」 */
  province?: string | null
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
  /** 考试级提示(构建期写入,如「设区市户籍要求不在职位表内」) */
  notices?: string[]
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
  /** 专业大类名 → 国家目录节点 id 集合(江苏) */
  catRefs?: Record<string, string[]>
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

export type FreshStatus = 'unknown' | 'none' | 'current' | 'reserved'
export type PoliticalStatus = 'unknown' | 'party' | 'prospective' | 'league' | 'masses'
export type CetLevel = 'unknown' | 'none' | '4' | '6'

export interface Profile {
  /** 空字符串表示用户尚未填写 */
  highestEdu: EduLevel | ''
  /** 是否已取得(或将取得)与最高学历对应的学位;null 表示尚未填写 */
  hasDegree: boolean | null
  ugMajorId: string | null
  pgMajorId: string | null
  /** 应届状态:unknown 尚未填写;none 非应届;current 当年届毕业生;reserved 择业期内未就业的往届生(视同应届) */
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
