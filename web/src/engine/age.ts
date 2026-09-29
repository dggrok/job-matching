import type { AgeRule, Position } from './types'

/** 出生年月界限,格式 YYYY-MM,可直接做字符串比较。 */
export interface AgeBounds {
  /** 最早允许的出生年月(含) */
  oldest: string
  /** 最晚允许的出生年月(含),即刚满最低年龄 */
  youngest: string
  /** 备注里写"放宽到 N 周岁"对应的最早出生年月(需满足特定条件,待确认) */
  relaxedOldest?: string
}

export function ym(year: number, month: number): string {
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`
}

/**
 * 计算某个职位的年龄界限。
 *
 * 口径与国考公告一致:"38 周岁以下(1986 年 10 月至 2007 年 10 月期间出生)",
 * 即报名年份为 Y、月份为 M 时,最早出生年月 = (Y - maxAge - 1, M)。
 *
 * - 应届硕士、博士研究生(freshPg)使用放宽后的上限;
 * - 市(地)级及以下公安民警职位(pos.police)使用更严的上限;
 * - 备注里写明的更严上限(rr.maxAge)优先。
 */
export function ageBounds(rule: AgeRule, pos: Position, freshPg: boolean): AgeBounds {
  let max = pos.police ? rule.policeMaxAge : rule.maxAge
  let maxFresh = pos.police ? rule.policeMaxAgeFreshPg : rule.maxAgeFreshPg
  const remarkMax = pos.rr.maxAge
  if (remarkMax) {
    max = Math.min(max, remarkMax)
    maxFresh = Math.max(max, Math.min(maxFresh, remarkMax))
  }
  const limit = freshPg ? maxFresh : max
  const bounds: AgeBounds = {
    oldest: ym(rule.refYear - limit - 1, rule.refMonth),
    youngest: ym(rule.refYear - rule.minAge, rule.refMonth),
  }
  if (pos.rr.ageRelaxedTo) {
    bounds.relaxedOldest = ym(rule.refYear - pos.rr.ageRelaxedTo - 1, rule.refMonth)
  }
  return bounds
}

export function formatYm(s: string): string {
  const [y, m] = s.split('-')
  return `${y}年${Number(m)}月`
}
