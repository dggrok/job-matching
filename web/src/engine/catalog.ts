import type { CatalogFile, CatalogRow } from './types'

export type Level = 'UG' | 'PG'

export interface CatalogNode {
  id: string
  name: string
  kind: string
  parent: string | null
  note: string | null
  children?: CatalogNode[]
}

function toNode(row: CatalogRow): CatalogNode {
  return { id: row[0], name: row[1], kind: row[2], parent: row[3], note: row[4] }
}

/** 专业目录:按 id 查节点、取祖先链、生成级联选择树。 */
export class Catalog {
  private nodes = new Map<string, CatalogNode>()
  readonly meta: CatalogFile['meta']

  constructor(file: CatalogFile) {
    this.meta = file.meta
    for (const row of [...file.UG, ...file.PG]) {
      const n = toNode(row)
      this.nodes.set(n.id, n)
    }
  }

  get(id: string): CatalogNode | undefined {
    return this.nodes.get(id)
  }

  name(id: string | null | undefined): string {
    return (id && this.nodes.get(id)?.name) || ''
  }

  /** 从自身到门类的 id 链,如 UG:080701 → UG:0807 → UG:08。 */
  chain(id: string): string[] {
    const out: string[] = []
    let cur: string | null = id
    while (cur) {
      out.push(cur)
      cur = this.nodes.get(cur)?.parent ?? null
    }
    return out
  }

  /** 生成某个层次的目录树(门类 → 专业类/一级学科 → 专业),供级联选择器使用。 */
  tree(level: Level): CatalogNode[] {
    const byParent = new Map<string | null, CatalogNode[]>()
    for (const n of this.nodes.values()) {
      if (!n.id.startsWith(level + ':')) continue
      const list = byParent.get(n.parent) ?? []
      list.push(n)
      byParent.set(n.parent, list)
    }
    const build = (parent: string | null): CatalogNode[] =>
      (byParent.get(parent) ?? []).map((n) => {
        const children = build(n.id)
        return children.length ? { ...n, children } : { ...n }
      })
    return build(null)
  }
}
