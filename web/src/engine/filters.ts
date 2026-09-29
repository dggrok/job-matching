import type { MatchResult, Position, Status } from './types'

/** 从工作地点里取省级名称:"河北省秦皇岛市" → "河北省";"北京市" → "北京市"。 */
export function provinceOf(location: string): string {
  const m = location.match(/^(北京市|天津市|上海市|重庆市|.+?省|.+?自治区|.+?特别行政区)/)
  return m ? m[1] : location || '未标注'
}

export interface Filters {
  keyword: string
  provinces: string[]
  sheets: string[]
  orgLevels: string[]
  attrs: string[]
  statuses: Status[]
  minHeadcount: number
}

export function emptyFilters(): Filters {
  return {
    keyword: '',
    provinces: [],
    sheets: [],
    orgLevels: [],
    attrs: [],
    statuses: ['ok', 'maybe'],
    minHeadcount: 0,
  }
}

export interface Row {
  pos: Position
  result: MatchResult
  province: string
}

export function applyFilters(rows: Row[], f: Filters): Row[] {
  const kw = f.keyword.trim().toLowerCase()
  return rows.filter((r) => {
    if (!f.statuses.includes(r.result.status)) return false
    if (f.provinces.length && !f.provinces.includes(r.province)) return false
    if (f.sheets.length && !f.sheets.includes(r.pos.sheet)) return false
    if (f.orgLevels.length && !f.orgLevels.includes(r.pos.orgLevel)) return false
    if (f.attrs.length && !f.attrs.includes(r.pos.attr)) return false
    if (f.minHeadcount > 0 && r.pos.headcount < f.minHeadcount) return false
    if (kw) {
      const hay = `${r.pos.org}${r.pos.unit}${r.pos.title}${r.pos.location}${r.pos.code}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
}

export type SortKey = 'headcount' | 'org' | 'status'

const STATUS_ORDER: Record<Status, number> = { ok: 0, maybe: 1, no: 2 }

export function sortRows(rows: Row[], key: SortKey): Row[] {
  const copy = [...rows]
  if (key === 'headcount') {
    copy.sort((a, b) => STATUS_ORDER[a.result.status] - STATUS_ORDER[b.result.status] || b.pos.headcount - a.pos.headcount)
  } else if (key === 'org') {
    copy.sort((a, b) => a.pos.org.localeCompare(b.pos.org, 'zh-Hans-CN') || a.pos.code.localeCompare(b.pos.code))
  } else {
    copy.sort((a, b) => STATUS_ORDER[a.result.status] - STATUS_ORDER[b.result.status])
  }
  return copy
}

export interface Summary {
  ok: number
  maybe: number
  no: number
  okHeadcount: number
  maybeHeadcount: number
}

export function summarize(rows: Row[]): Summary {
  const s: Summary = { ok: 0, maybe: 0, no: 0, okHeadcount: 0, maybeHeadcount: 0 }
  for (const r of rows) {
    s[r.result.status] += 1
    if (r.result.status === 'ok') s.okHeadcount += r.pos.headcount
    if (r.result.status === 'maybe') s.maybeHeadcount += r.pos.headcount
  }
  return s
}

const STATUS_LABEL: Record<Status, string> = { ok: '符合', maybe: '待确认', no: '不符合' }

export const POLITICAL_LABEL: Record<string, string> = {
  any: '不限',
  party: '中共党员',
  partyOrLeague: '中共党员或共青团员',
  unknown: '未识别',
}

/** 导出为 CSV(带 BOM,Excel 直接打开不乱码)。 */
export function toCsv(rows: Row[], majorText: (p: Position) => string): string {
  const head = ['匹配状态', '部门名称', '用人司局', '招考职位', '职位代码', '部门代码', '招考人数', '工作地点', '学历', '专业', '政治面貌', '基层经历', '备注', '待确认或不符合原因']
  const esc = (v: string | number) => `"${String(v).replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`
  const lines = [head.map(esc).join(',')]
  for (const r of rows) {
    const p = r.pos
    const why = r.result.reasons
      .filter((x) => x.level !== 'pass')
      .map((x) => `${x.field}:${x.text}`)
      .join(' | ')
    lines.push(
      [STATUS_LABEL[r.result.status], p.org, p.unit, p.title, p.code, p.deptCode, p.headcount, p.location, p.eduText, majorText(p), POLITICAL_LABEL[p.political] ?? p.political, p.grassroots, p.remark, why]
        .map(esc)
        .join(','),
    )
  }
  return '\ufeff' + lines.join('\r\n')
}
