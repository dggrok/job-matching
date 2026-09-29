import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ageBounds } from './age'
import { Catalog } from './catalog'
import { applyFilters, emptyFilters, provinceOf, summarize, type Row } from './filters'
import { matchPosition, type MatchContext } from './match'
import type {
  CatalogFile,
  ExamData,
  ExamMeta,
  MajorRule,
  MajorToken,
  Manifest,
  Position,
  Profile,
} from './types'

const DATA = resolve(__dirname, '../../public/data')
const hasData = existsSync(resolve(DATA, 'catalog.json'))

const catalogFile: CatalogFile | null = hasData
  ? JSON.parse(readFileSync(resolve(DATA, 'catalog.json'), 'utf-8'))
  : null

const exam: ExamMeta = {
  id: 'guokao-2026',
  name: 't',
  type: 'guokao',
  year: 2026,
  graduateYear: 2026,
  source: '',
  pending: false,
  file: null,
  ageRule: {
    refYear: 2025,
    refMonth: 10,
    minAge: 18,
    maxAge: 38,
    maxAgeFreshPg: 43,
    policeMaxAge: 30,
    policeMaxAgeFreshPg: 35,
  },
}

/** 用户画像 #1:本科、电子信息工程、非应届、男、1992-03 出生、群众。 */
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

function token(over: Partial<MajorToken> & { refs: string[] }): MajorToken {
  return { raw: over.name ?? 'x', name: 'x', codes: [], partial: false, resolved: true, qualifiers: [], ...over }
}

function rule(tokens: MajorToken[], level: 'UG' | 'PG' | 'ANY' = 'ANY', text = 'x'): MajorRule {
  return { text, unlimited: false, segments: [{ level, tokens }], warnings: [] }
}

function pos(over: Partial<Position> = {}): Position {
  return {
    id: 'p1',
    code: '1',
    deptCode: '0',
    org: '某局',
    unit: '',
    orgType: '',
    orgLevel: '县（区）级及以下',
    title: '职位',
    examCategory: '',
    attr: '普通职位',
    dist: '',
    intro: '',
    headcount: 1,
    location: '浙江省杭州市',
    hukou: '',
    edu: ['本科', '硕士', '博士'],
    eduText: '本科及以上',
    degree: 'matchHighest',
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

const describeIf = hasData ? describe : describe.skip

describeIf('匹配引擎(手工用例)', () => {
  const catalog = new Catalog(catalogFile!)
  const ctxFor = (profile: Profile, r: MajorRule): MatchContext => ({
    profile,
    exam,
    catalog,
    majorRules: { m1: r },
  })
  const eeClass = rule([token({ name: '电子信息类', refs: ['UG:0807'] })])

  it('全部满足 → ok', () => {
    const res = matchPosition(pos(), ctxFor(me, eeClass))
    expect(res.status).toBe('ok')
  })

  it('学历:仅限硕士,本科不符合', () => {
    const res = matchPosition(pos({ edu: ['硕士'], eduText: '仅限硕士研究生' }), ctxFor(me, eeClass))
    expect(res.status).toBe('no')
    expect(res.reasons.find((r) => r.field === '学历')?.level).toBe('fail')
  })

  it('应届:限应届,非应届不符合;限 2026 届,往届生不符合', () => {
    expect(matchPosition(pos({ rr: { freshOnly: true } }), ctxFor(me, eeClass)).status).toBe('no')
    const reserved = { ...me, freshStatus: 'reserved' as const }
    expect(matchPosition(pos({ rr: { freshOnly: true, gradYear: 2026 } }), ctxFor(reserved, eeClass)).status).toBe('no')
    expect(matchPosition(pos({ rr: { freshOnly: true } }), ctxFor(reserved, eeClass)).status).toBe('maybe')
    const current = { ...me, freshStatus: 'current' as const }
    expect(matchPosition(pos({ rr: { freshOnly: true, gradYear: 2026 } }), ctxFor(current, eeClass)).status).toBe('ok')
  })

  it('性别与政治面貌', () => {
    expect(matchPosition(pos({ rr: { gender: 'female' } }), ctxFor(me, eeClass)).status).toBe('no')
    expect(matchPosition(pos({ rr: { gender: 'male' } }), ctxFor(me, eeClass)).status).toBe('ok')
    expect(matchPosition(pos({ political: 'party' }), ctxFor(me, eeClass)).status).toBe('no')
    expect(matchPosition(pos({ political: 'party' }), ctxFor({ ...me, political: 'prospective' }, eeClass)).status).toBe('ok')
    expect(matchPosition(pos({ political: 'partyOrLeague' }), ctxFor({ ...me, political: 'league' }, eeClass)).status).toBe('ok')
    expect(matchPosition(pos({ rr: { gender: 'male' } }), ctxFor({ ...me, gender: '' }, eeClass)).status).toBe('maybe')
  })

  it('基层经历与服务基层项目', () => {
    expect(matchPosition(pos({ grassroots: 2 }), ctxFor(me, eeClass)).status).toBe('no')
    expect(matchPosition(pos({ grassroots: 2 }), ctxFor({ ...me, grassrootsYears: 3 }, eeClass)).status).toBe('ok')
    const limited = pos({ grassroots: 2, projects: ['village', 'sanzhi'] })
    expect(matchPosition(limited, ctxFor(me, eeClass)).status).toBe('no')
    expect(matchPosition(limited, ctxFor({ ...me, projects: ['sanzhi'], grassrootsYears: 2 }, eeClass)).status).toBe('ok')
    // 有年限但没选项目 → 待确认(口径需核对报考指南)
    expect(matchPosition(limited, ctxFor({ ...me, grassrootsYears: 2 }, eeClass)).status).toBe('maybe')
  })

  it('年龄:一般职位与公安民警职位', () => {
    expect(matchPosition(pos(), ctxFor({ ...me, birth: '1986-10' }, eeClass)).status).toBe('ok')
    expect(matchPosition(pos(), ctxFor({ ...me, birth: '1986-09' }, eeClass)).status).toBe('no')
    expect(matchPosition(pos(), ctxFor({ ...me, birth: '2007-11' }, eeClass)).status).toBe('no')
    // 市(地)级及以下公安民警 30 周岁以下(1994 年 10 月以后出生)
    const police = pos({ police: true })
    expect(matchPosition(police, ctxFor(me, eeClass)).status).toBe('no')
    expect(matchPosition(police, ctxFor({ ...me, birth: '1994-10' }, eeClass)).status).toBe('ok')
    // 出生年月未填 → 待确认
    expect(matchPosition(pos(), ctxFor({ ...me, birth: '' }, eeClass)).status).toBe('maybe')
  })

  it('年龄:应届硕博放宽到 43 周岁;备注更严上限;备注放宽待确认', () => {
    const master = { ...me, highestEdu: '硕士' as const, pgMajorId: 'PG:0854', ugMajorId: null, birth: '1984-01' }
    const pgRule = rule([token({ name: '电子信息', refs: ['PG:0854'] })])
    expect(matchPosition(pos(), ctxFor(master, pgRule)).status).toBe('no')
    const fresh = { ...master, freshStatus: 'current' as const }
    expect(matchPosition(pos({ rr: { freshOnly: true } }), ctxFor(fresh, pgRule)).status).toBe('ok')
    // 备注:报考年龄不超过 30 周岁
    expect(matchPosition(pos({ rr: { maxAge: 30 } }), ctxFor(me, eeClass)).status).toBe('no')
    // 备注:年龄放宽到 43 周岁(需特定条件)→ 1985 年出生超过一般上限但在放宽线内 → 待确认
    expect(matchPosition(pos({ rr: { ageRelaxedTo: 43 } }), ctxFor({ ...me, birth: '1985-01' }, eeClass)).status).toBe('maybe')
  })

  it('专业:命中专业类 → ok;不在要求内 → no', () => {
    expect(matchPosition(pos(), ctxFor(me, eeClass)).status).toBe('ok')
    const cs = rule([token({ name: '计算机类', refs: ['UG:0809'] })])
    const res = matchPosition(pos(), ctxFor(me, cs))
    expect(res.status).toBe('no')
    expect(res.reasons.find((r) => r.field === '专业')?.level).toBe('fail')
  })

  it('专业:门类、具体专业、其他层次的 refs', () => {
    expect(matchPosition(pos(), ctxFor(me, rule([token({ refs: ['UG:08'] })]))).status).toBe('ok')
    expect(matchPosition(pos(), ctxFor(me, rule([token({ refs: ['UG:080701'] })]))).status).toBe('ok')
    // 研究生一级学科不会命中本科用户
    expect(matchPosition(pos(), ctxFor(me, rule([token({ refs: ['PG:0810'] })]))).status).toBe('no')
  })

  it('专业:不含清单命中 → 视为不符合;限定/推断命中 → 待确认', () => {
    const excl = token({
      refs: ['UG:0807'],
      qualifiers: [{ kind: 'exclude', text: '不含电子信息工程', refs: ['UG:080701'] }],
    })
    expect(matchPosition(pos(), ctxFor(me, rule([excl]))).status).toBe('no')
    const restrict = token({ refs: ['UG:0807'], qualifiers: [{ kind: 'restrict', text: '限通信方向' }] })
    expect(matchPosition(pos(), ctxFor(me, rule([restrict]))).status).toBe('maybe')
    expect(matchPosition(pos(), ctxFor(me, rule([token({ refs: ['UG:0807'], partial: true })]))).status).toBe('maybe')
    // 另一个 token 明确命中时,以明确命中为准
    expect(matchPosition(pos(), ctxFor(me, rule([restrict, token({ refs: ['UG:080701'] })]))).status).toBe('ok')
  })

  it('专业:未解析条目按学历层次判断', () => {
    const pgLike = token({ resolved: false, refs: [], name: '民商法学', likelyLevel: 'PG' })
    const ugLike = token({ resolved: false, refs: [], name: '经济金融类', likelyLevel: 'UG' })
    // 本科用户:研究生口径的二级学科名不相关 → 直接不符合
    expect(matchPosition(pos(), ctxFor(me, rule([pgLike]))).status).toBe('no')
    // 本科口径的目录外名称 → 待确认
    expect(matchPosition(pos(), ctxFor(me, rule([ugLike]))).status).toBe('maybe')
  })

  it('专业:不限、以及只填了另一层次专业', () => {
    const unlimited: MajorRule = { text: '专业不限', unlimited: true, segments: [], warnings: [] }
    expect(matchPosition(pos(), ctxFor(me, unlimited)).status).toBe('ok')
    // 本科用户但只在研究生分段有要求 → 待确认
    expect(matchPosition(pos(), ctxFor(me, rule([token({ refs: ['PG:0810'] })], 'PG'))).status).toBe('maybe')
    // 没选专业 → 待确认
    expect(matchPosition(pos(), ctxFor({ ...me, ugMajorId: null }, eeClass)).status).toBe('maybe')
  })

  it('专业:备注写明各学历阶段对应专业之一即可 → 本科与研究生专业都参与', () => {
    const both = { ...me, highestEdu: '硕士' as const, pgMajorId: 'PG:0301', ugMajorId: 'UG:080701', birth: '1992-03' }
    const r = rule([token({ refs: ['UG:0807'] })], 'UG')
    // 默认以最高学历(研究生)对应专业为准,而该规则只有本科分段 → 待确认
    expect(matchPosition(pos(), ctxFor(both, r)).status).toBe('maybe')
    // 备注允许任一学历阶段 → 本科专业命中
    expect(matchPosition(pos({ rr: { majorAnyLevel: true } }), ctxFor(both, r)).status).toBe('ok')
  })

  it('英语等级', () => {
    const need4 = pos({ rr: { cet: { ANY: 4 } } })
    expect(matchPosition(need4, ctxFor(me, eeClass)).status).toBe('maybe') // 未填
    expect(matchPosition(need4, ctxFor({ ...me, cet: '4' }, eeClass)).status).toBe('ok')
    expect(matchPosition(need4, ctxFor({ ...me, cet: 'none' }, eeClass)).status).toBe('no')
    const alt = pos({ rr: { cet: { ANY: 4 }, cetAltAllowed: true } })
    expect(matchPosition(alt, ctxFor({ ...me, cet: 'none', hasAltEnglishCert: true }, eeClass)).status).toBe('ok')
    // 本科生四级、研究生六级:本科用户只需四级
    const split = pos({ rr: { cet: { UG: 4, PG: 6 } } })
    expect(matchPosition(split, ctxFor({ ...me, cet: '4' }, eeClass)).status).toBe('ok')
  })

  it('户籍、证书、工作经历只给出提示,不误判为符合', () => {
    expect(matchPosition(pos({ rr: { residency: ['限内蒙古户籍或生源'] } }), ctxFor(me, eeClass)).status).toBe('maybe')
    expect(
      matchPosition(pos({ rr: { residency: ['限内蒙古户籍或生源'] } }), ctxFor({ ...me, originProvince: '内蒙古' }, eeClass)).status,
    ).toBe('ok')
    expect(matchPosition(pos({ rr: { legalQualification: true, certificates: ['取得法律职业资格证书(A类)'] } }), ctxFor(me, eeClass)).status).toBe('no')
    expect(
      matchPosition(
        pos({ rr: { legalQualification: true, certificates: ['取得法律职业资格证书(A类)'] } }),
        ctxFor({ ...me, legalQualification: true }, eeClass),
      ).status,
    ).toBe('ok')
    expect(matchPosition(pos({ rr: { workExperience: ['应具有2年以上相关工作经历'] } }), ctxFor(me, eeClass)).status).toBe('maybe')
  })
})

describe('年龄界限计算', () => {
  const p = pos()
  it('2026 年度公告口径:38 周岁以下 = 1986-10 至 2007-10 期间出生', () => {
    const b = ageBounds(exam.ageRule!, p, false)
    expect(b.oldest).toBe('1986-10')
    expect(b.youngest).toBe('2007-10')
    expect(ageBounds(exam.ageRule!, p, true).oldest).toBe('1981-10')
    expect(ageBounds(exam.ageRule!, pos({ police: true }), false).oldest).toBe('1994-10')
    expect(ageBounds(exam.ageRule!, pos({ police: true }), true).oldest).toBe('1989-10')
  })
})

describe('省份提取', () => {
  it.each([
    ['北京市', '北京市'],
    ['河北省秦皇岛市', '河北省'],
    ['内蒙古自治区呼和浩特市', '内蒙古自治区'],
    ['广西壮族自治区南宁市', '广西壮族自治区'],
    ['', '未标注'],
  ])('%s → %s', (loc, expected) => {
    expect(provinceOf(loc)).toBe(expected)
  })
})

// ---------------------------------------------------------------------------
// 真实数据不变式:用 2026 年度国考职位表全量数据检查引擎行为
// ---------------------------------------------------------------------------
const examFile = resolve(DATA, 'guokao-2026/positions.json')
const describeReal = hasData && existsSync(examFile) ? describe : describe.skip

describeReal('真实数据(2026 国考)', () => {
  const catalog = new Catalog(catalogFile!)
  const manifest: Manifest = JSON.parse(readFileSync(resolve(DATA, 'manifest.json'), 'utf-8'))
  const realExam = manifest.exams.find((e) => e.id === 'guokao-2026')!
  const data: ExamData = JSON.parse(readFileSync(examFile, 'utf-8'))
  const ctx: MatchContext = { profile: me, exam: realExam, catalog, majorRules: data.majorRules }

  const rows: Row[] = data.positions.map((p) => ({
    pos: p,
    result: matchPosition(p, ctx),
    province: provinceOf(p.location),
  }))
  const summary = summarize(rows)

  it('所有职位都能算出结果,且有一定数量的可报职位', () => {
    expect(rows.length).toBe(20714)
    // 该画像为非应届(约 67% 职位限应届)、无党员身份与基层经历,可报职位天然有限。
    // 2026 样表实测符合+待确认为 492 个,这里只做数量级的回归保护。
    expect(summary.ok + summary.maybe).toBeGreaterThan(200)
    expect(summary.ok + summary.maybe).toBeLessThan(3000)
    console.log('画像#1(本科·电子信息工程·非应届·男·1992-03)结果:', summary)
  })

  it('不变式:被判为符合的职位,必须满足所有硬性字段', () => {
    for (const { pos: p, result } of rows) {
      if (result.status !== 'ok') continue
      expect(p.edu).toContain('本科')
      expect(p.rr.freshOnly).toBeFalsy()
      expect(p.police).toBeFalsy() // 1992 年出生超过 30 周岁警察线
      expect(p.rr.gender === undefined || p.rr.gender === 'male').toBe(true)
      expect(p.political).toBe('any') // 群众
      expect(p.grassroots).toBe(0)
      expect(p.projects).toEqual([])
    }
  })

  it('不变式:限应届的职位对非应届用户一律不符合', () => {
    for (const { pos: p, result } of rows) {
      if (p.rr.freshOnly) expect(result.status).toBe('no')
    }
  })

  it('不变式:仅限研究生的职位对本科用户一律不符合', () => {
    for (const { pos: p, result } of rows) {
      if (!p.edu.includes('本科')) expect(result.status).toBe('no')
    }
  })

  it('专业要求电子信息类且条件宽松的职位,应被判为符合或待确认', () => {
    const cand = data.positions.filter((p) => {
      const r = data.majorRules[p.majorId]
      const refsUG = r.segments.flatMap((s) => (s.level !== 'PG' ? s.tokens : [])).flatMap((t) => t.refs)
      return (
        refsUG.includes('UG:0807') &&
        p.edu.includes('本科') &&
        !p.rr.freshOnly &&
        !p.police &&
        p.political === 'any' &&
        p.grassroots === 0 &&
        !p.rr.gender &&
        p.rr.maxAge === undefined
      )
    })
    expect(cand.length).toBeGreaterThan(20)
    const bad = cand.filter((p) => {
      const r = rows.find((x) => x.pos.id === p.id)!
      return r.result.status === 'no'
    })
    // 允许极少数因专业限定(如不含清单)被判为不符合,但不应大量出现
    expect(bad.length / cand.length).toBeLessThan(0.15)
  })

  it('筛选:按省份与状态过滤', () => {
    const f = emptyFilters()
    f.provinces = ['浙江省']
    f.statuses = ['ok', 'maybe']
    const out = applyFilters(rows, f)
    expect(out.length).toBeGreaterThan(0)
    expect(out.every((r) => r.province === '浙江省' && r.result.status !== 'no')).toBe(true)
  })
})
