import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ageBounds } from './age'
import { Catalog } from './catalog'
import { regionOf, summarize, type Row } from './filters'
import { matchPosition, type MatchContext } from './match'
import type { CatalogFile, ExamData, ExamMeta, MajorRule, MajorToken, Manifest, Position, Profile } from './types'

const DATA = resolve(__dirname, '../../public/data')
const hasData = existsSync(resolve(DATA, 'catalog.json'))
const catalogFile: CatalogFile | null = hasData
  ? JSON.parse(readFileSync(resolve(DATA, 'catalog.json'), 'utf-8'))
  : null

const exam: ExamMeta = {
  id: 'zhejiang-2026',
  name: 't',
  type: 'zhejiang',
  kind: 'shengkao',
  province: '浙江',
  year: 2026,
  graduateYear: 2026,
  source: '',
  pending: false,
  file: null,
  ageRule: { refYear: 2025, refMonth: 11, minAge: 18, maxAge: 38, maxAgeFreshPg: 43, policeMaxAge: 30, policeMaxAgeFreshPg: 35 },
}

/** 本科、电子信息工程、非应届、男、1992-03 出生、群众。 */
const me: Profile = {
  highestEdu: '本科',
  hasDegree: true,
  ugMajorId: 'UG:080701',
  pgMajorId: null,
  freshStatus: 'none',
  birth: '1992-03',
  gender: 'male',
  political: 'masses',
  grassrootsYears: 0,
  projects: [],
  cet: 'unknown',
  hasAltEnglishCert: false,
  legalQualification: false,
  originProvince: '',
}

function token(over: Partial<MajorToken>): MajorToken {
  return { raw: 'x', name: 'x', codes: [], refs: [], partial: false, resolved: true, qualifiers: [], ...over }
}

function pos(over: Partial<Position> = {}): Position {
  return {
    id: 'p1',
    code: '1',
    deptCode: '0',
    org: '某局',
    unit: '',
    orgType: '',
    orgLevel: '',
    title: '职位',
    examCategory: '',
    attr: '',
    dist: '',
    intro: '',
    headcount: 1,
    location: '杭州市',
    hukou: '',
    edu: ['本科', '硕士', '博士'],
    eduText: '本科及以上',
    degree: 'none',
    political: 'any',
    grassroots: 0,
    projects: [],
    majorId: 'm1',
    remark: '',
    rr: {},
    interviewRatio: '',
    skillTest: '',
    site: '',
    phones: [],
    sheet: '',
    ...over,
  }
}

const unlimited: MajorRule = { text: '不限', unlimited: true, segments: [], warnings: [] }

const describeIf = hasData ? describe : describe.skip

describeIf('省考字段的匹配行为(手工用例)', () => {
  const catalog = new Catalog(catalogFile!)
  const run = (p: Position, profile: Profile = me, rule: MajorRule = unlimited, catRefs?: Record<string, string[]>) =>
    matchPosition(p, { profile, exam, catalog, majorRules: { m1: rule }, catRefs } as MatchContext)
  const level = (res: ReturnType<typeof run>, field: string) => res.reasons.find((r) => r.field === field)?.level

  it('职位自带的年龄线优先:限 30 周岁以下时 33 岁不符合', () => {
    expect(run(pos()).status).toBe('ok')
    const res = run(pos({ ageMax: 30, ageMaxFresh: 30 }))
    expect(res.status).toBe('no')
    expect(level(res, '年龄')).toBe('fail')
  })

  it('职位自带的年龄线:应届硕博使用放宽后的上限', () => {
    const b = ageBounds(exam.ageRule!, pos({ ageMax: 38, ageMaxFresh: 43 }), true)
    expect(b.oldest).toBe('1981-11')
    expect(ageBounds(exam.ageRule!, pos({ ageMax: 38, ageMaxFresh: 43 }), false).oldest).toBe('1986-11')
    expect(ageBounds(exam.ageRule!, pos({ ageMin: 20 }), false).minAge).toBe(20)
  })

  it('年龄按专门规定执行的职位:通过时也只能待确认', () => {
    const res = run(pos({ rr: { ageSpecial: true } }))
    expect(level(res, '年龄')).toBe('warn')
    expect(res.status).toBe('maybe')
  })

  it('其他硬条件(notes)与特定身份(identity)一律待确认', () => {
    const a = run(pos({ rr: { notes: ['取得大学英语六级考试证书'] } }))
    expect(a.status).toBe('maybe')
    expect(level(a, '其他条件')).toBe('warn')
    const b = run(pos({ rr: { identity: ['限优秀村干部'] } }))
    expect(b.status).toBe('maybe')
    expect(level(b, '特定身份')).toBe('warn')
  })

  it('应届类职位另有开放对象(freshAlt)时,往届生待确认而非不符合', () => {
    expect(run(pos({ rr: { freshOnly: true, gradYear: 2026 } })).status).toBe('no')
    const res = run(pos({ rr: { freshOnly: true, gradYear: 2026, freshAlt: '服务期满的西部计划志愿者' } }))
    expect(res.status).toBe('maybe')
    expect(level(res, '应届/往届')).toBe('warn')
  })

  it('服务基层项目职位允许其他身份(altIdentity)时,没有项目经历待确认', () => {
    expect(run(pos({ projects: ['west'] })).status).toBe('no')
    const res = run(pos({ projects: ['west'], rr: { altIdentity: '乡镇事业编制人员' } }))
    expect(res.status).toBe('maybe')
    expect(level(res, '基层经历')).toBe('warn')
    expect(run(pos({ projects: ['west', 'shanhai'] }), { ...me, projects: ['shanhai'] }).status).toBe('ok')
  })

  it('本科阶段要求只对研究生学历报考者生效', () => {
    const p = pos({ rr: { ugStage: ['本科阶段为法律类专业并取得相应学位'] } })
    expect(run(p).status).toBe('ok')
    const pg: Profile = { ...me, highestEdu: '硕士', pgMajorId: 'PG:0810', ugMajorId: 'UG:080701' }
    expect(level(run(p, pg), '本科阶段')).toBe('warn')
  })

  it('专业大类:通过 catRefs 引用国家目录节点', () => {
    const rule: MajorRule = {
      text: '电子信息类',
      unlimited: false,
      segments: [{ level: 'ANY', tokens: [token({ name: '电子信息类', cat: '电子信息类' })] }],
      warnings: [],
    }
    expect(level(run(pos(), me, rule, { 电子信息类: ['UG:080701', 'UG:080703'] }), '专业')).toBe('pass')
    expect(level(run(pos(), me, rule, { 电子信息类: ['UG:080901'] }), '专业')).toBe('fail')
    expect(level(run(pos(), me, rule, undefined), '专业')).toBe('fail')
  })
})

describe('省考地区提取', () => {
  it.each([
    ['杭州市', '杭州市'],
    ['省级', '省级'],
    ['南京市玄武区', '南京市'],
    ['苏州市昆山市', '苏州市'],
    ['', '未标注'],
  ])('%s → %s', (loc, expected) => {
    expect(regionOf(loc, 'shengkao')).toBe(expected)
  })
  it('国考仍按省份提取', () => {
    expect(regionOf('河北省秦皇岛市', 'guokao')).toBe('河北省')
  })
})

// ---------------------------------------------------------------------------
// 真实数据不变式
// ---------------------------------------------------------------------------
const manifestFile = resolve(DATA, 'manifest.json')

function realSuite(examId: string, expectedCount: number) {
  const file = resolve(DATA, `${examId}/positions.json`)
  const describeReal = hasData && existsSync(file) && existsSync(manifestFile) ? describe : describe.skip
  describeReal(`真实数据(${examId})`, () => {
    const catalog = new Catalog(catalogFile!)
    const manifest: Manifest = JSON.parse(readFileSync(manifestFile, 'utf-8'))
    const realExam = manifest.exams.find((e) => e.id === examId)!
    const data: ExamData = JSON.parse(readFileSync(file, 'utf-8'))
    const ctx: MatchContext = { profile: me, exam: realExam, catalog, majorRules: data.majorRules, catRefs: data.catRefs }
    const rows: Row[] = data.positions.map((p) => ({
      pos: p,
      result: matchPosition(p, ctx),
      province: regionOf(p.location, realExam.kind),
    }))
    const summary = summarize(rows)

    it('manifest 标注为省考,所有职位都能算出结果', () => {
      expect(realExam.kind).toBe('shengkao')
      expect(rows.length).toBe(expectedCount)
      expect(summary.ok + summary.maybe).toBeGreaterThan(100)
      console.log(`${examId} 画像#1 结果:`, summary)
    })

    it('不变式:被判为符合的职位,不含任何需人工核对的条件', () => {
      for (const { pos: p, result } of rows) {
        if (result.status !== 'ok') continue
        expect(p.rr.notes ?? []).toEqual([])
        expect(p.rr.identity ?? []).toEqual([])
        expect(p.rr.ageSpecial).toBeFalsy()
        expect(p.rr.freshOnly).toBeFalsy()
        expect(p.edu).toContain('本科')
        expect(p.rr.gender === undefined || p.rr.gender === 'male').toBe(true)
      }
    })

    it('不变式:出生年月不在职位年龄线内的一律不符合', () => {
      for (const { pos: p, result } of rows) {
        if (p.ageMax !== undefined && p.ageMax < 33) expect(result.status).toBe('no')
      }
    })

    it('catRefs 里的节点都存在于专业目录', () => {
      for (const ids of Object.values(data.catRefs ?? {})) {
        for (const id of ids) expect(catalog.name(id), id).toBeTruthy()
      }
    })
  })
}

realSuite('zhejiang-2026', 4004)
realSuite('jiangsu-2026', 6157)
