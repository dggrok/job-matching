import type { Catalog } from './catalog'
import type { MajorRule, MajorToken, Position, Profile, ReasonLevel } from './types'

export interface MajorVerdict {
  level: ReasonLevel
  text: string
}

/** 用户的最高学历对应哪个专业层次。 */
export function userLevel(profile: Profile): 'UG' | 'PG' {
  return profile.highestEdu === '硕士' || profile.highestEdu === '博士' ? 'PG' : 'UG'
}

function shorten(s: string, n = 60): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

/**
 * 专业匹配。
 *
 * 语义:
 * 1. 默认以用户最高学历对应的专业为准;备注写明"各学历阶段对应专业之一即可"时,本科和研究生专业都参与匹配。
 * 2. 用户专业的祖先链(专业 → 专业类 → 门类)与 token 的 refs 有交集即命中。
 * 3. 命中但带"限定"、或仅通过推断/二级学科前缀命中 → 待确认;命中"不含"清单 → 视为未命中。
 * 4. 没命中但存在无法解析、且很可能属于用户学历层次的条目 → 待确认,而不是直接判不符合。
 */
export function matchMajor(
  rule: MajorRule,
  pos: Position,
  profile: Profile,
  catalog: Catalog,
  catRefs?: Record<string, string[]>,
): MajorVerdict {
  if (rule.unlimited) return { level: 'pass', text: '专业不限' }

  const ugId = profile.ugMajorId
  const pgId = profile.pgMajorId
  const lvl = userLevel(profile)
  const anyLevel = !!pos.rr.majorAnyLevel

  // 参与匹配的层次及其祖先链
  const chains: Partial<Record<'UG' | 'PG', Set<string>>> = {}
  const wantUG = anyLevel || lvl === 'UG'
  const wantPG = anyLevel || lvl === 'PG'
  if (wantUG && ugId) chains.UG = new Set(catalog.chain(ugId))
  if (wantPG && pgId) chains.PG = new Set(catalog.chain(pgId))
  const levelsPresent = Object.keys(chains) as ('UG' | 'PG')[]

  if (levelsPresent.length === 0) {
    const need = lvl === 'UG' ? '本科' : '研究生'
    return { level: 'warn', text: `尚未填写你的${need}专业,无法判断专业是否符合` }
  }

  const userNames = levelsPresent
    .map((l) => catalog.name(l === 'UG' ? ugId : pgId))
    .filter(Boolean)
    .join(' / ')

  // 该职位专业规则里,哪些分段适用于这位用户
  const applicable = rule.segments.filter((s) => {
    const segLevels = s.level === 'ANY' ? (['UG', 'PG'] as const) : ([s.level] as const)
    return segLevels.some((l) => levelsPresent.includes(l))
  })
  if (applicable.length === 0) {
    return {
      level: 'warn',
      text: `专业要求未针对你的学历层次单独说明(要求:${shorten(rule.text)}),请核对招考简章`,
    }
  }

  const chainSet = new Set<string>()
  for (const l of levelsPresent) chains[l]!.forEach((id) => chainSet.add(id))

  let bestMaybe: string | null = null
  let excludedName: string | null = null
  const unresolvedNames: string[] = []

  for (const seg of applicable) {
    for (const t of seg.tokens) {
      if (!t.resolved) {
        if (t.likelyLevel && levelsPresent.includes(t.likelyLevel)) {
          unresolvedNames.push(t.name || t.raw)
        }
        continue
      }
      // 江苏的专业大类:节点集合放在 catRefs 里统一存放,规则里只有引用
      const refs = t.cat ? (catRefs?.[t.cat] ?? []) : t.refs
      if (!refs.some((r) => chainSet.has(r))) continue
      const verdict = evaluateHit(t, chainSet)
      if (verdict === 'excluded') {
        excludedName = t.name
        continue
      }
      if (verdict.level === 'pass') {
        return { level: 'pass', text: `你的专业「${userNames}」符合:${t.name || t.raw}` }
      }
      bestMaybe = bestMaybe ?? verdict.text
    }
  }

  if (bestMaybe) return { level: 'warn', text: bestMaybe }
  if (unresolvedNames.length) {
    const shown = [...new Set(unresolvedNames)].slice(0, 3).join('、')
    return {
      level: 'warn',
      text: `专业要求含目录外名称(${shown}),无法自动判断,请核对招考简章`,
    }
  }
  if (excludedName) {
    return { level: 'fail', text: `你的专业「${userNames}」在「${excludedName}」的不含范围内` }
  }
  return {
    level: 'fail',
    text: `你的专业「${userNames}」不在要求范围内(要求:${shorten(rule.text)})`,
  }
}

type Hit = 'excluded' | { level: 'pass' | 'warn'; text: string }

function evaluateHit(token: MajorToken, chain: Set<string>): Hit {
  for (const q of token.qualifiers) {
    if (q.kind === 'exclude' && q.refs.some((r) => chain.has(r))) return 'excluded'
  }
  const restrict = token.qualifiers.find((q) => q.kind === 'restrict')
  if (restrict) {
    return {
      level: 'warn',
      text: `专业属于「${token.name}」,但有附加限定:${restrict.text},请核对`,
    }
  }
  if (token.partial) {
    return {
      level: 'warn',
      text: `专业可能属于「${token.name}」(按二级学科或推断映射命中),请核对招考简章`,
    }
  }
  return { level: 'pass', text: '' }
}
