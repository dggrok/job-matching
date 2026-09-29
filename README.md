# 考公职位匹配筛选

根据个人的专业、学历、年龄、政治面貌等条件,从官方公布的公务员招考职位表中筛选出**符合报考条件**的岗位,并说明每个岗位符合、待确认或不符合的原因。

> 详细方案、调研结论、实现现状、维护指南见 [`考公职位匹配筛选-方案.md`](./考公职位匹配筛选-方案.md)。**接手前先看文末的「实现现状与维护指南」和「已知局限」。**

## 范围与进度

| 期数 | 内容 | 状态 |
| --- | --- | --- |
| 一期 | 国考(中央机关及其直属机构) | **MVP 已完成**,当前使用 2026 年度职位表作为开发样本 |
| 一期 | 导入 2027 年度国考职位表 | 等待官方发布(预计 2026-10-14) |
| 二期 | 省考:浙江、江苏 | 未开始 |

清单共 20 步,已完成 1 至 18(金标准集、Playwright 脚本、人工抽检尚未做),19 等待数据,20 属二期。逐步记录见方案文档。

## 快速开始

```bash
# 1. 数据管线(首次)
cd data-pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 需要把职位表 xls 放到 data-pipeline/raw/(见下方"数据来源"),然后:
.venv/bin/python -m src.build --all
.venv/bin/python -m pytest -q          # 39 个用例

# 2. 前端
cd ../web
pnpm install
pnpm dev                                # http://localhost:5173
pnpm test && pnpm typecheck && pnpm build
```

`web/public/data/` 里已带有 2026 年度的构建结果,不跑管线也可以直接 `pnpm dev` 看效果。

## 在线访问

推送到 `main` 后,GitHub Actions(`.github/workflows/pages.yml`)会自动构建 `web/` 并发布到 GitHub Pages:

https://dggrok.github.io/job-matching/

仓库需要是公开的,并且在 Settings → Pages 里把 Source 设为 GitHub Actions。本地 `pnpm dev` / `pnpm build` 不受影响,只有在 Actions 里构建时才会加上 `/job-matching/` 前缀。

## 使用方式

1. 打开「我的条件」,填写最高学历、专业、应届状态、出生年月、政治面貌等。信息只保存在本机浏览器。
2. 「匹配结果」按三态展示:符合、待确认、不符合。点击顶部统计卡片可显示或隐藏对应状态,还可按省份、机关类别、机构层级、职位属性、人数筛选,排序,导出 CSV。
3. 点击「详情」查看逐项匹配原因、原始专业与备注原文,可收藏;在「收藏与对比」里勾选 2 到 5 个职位横向对比。

## 目录说明

```
job-matching/
├── 考公职位匹配筛选-方案.md   # 方案、进度记录、维护指南(主文档)
├── README.md                   # 本文件
├── data-pipeline/              # Python 离线数据管线
│   ├── raw/                    # 人工下载的原始职位表(不入库)
│   ├── catalogs/source/        # 专业目录文本(教育部目录转出的文本,入库)
│   ├── config/                 # exams.yaml(考试元信息与年龄口径)、majors-alias.yaml(专业别名)
│   ├── src/                    # catalog 目录索引、importers 导入、normalize 归一、validate、build
│   ├── reports/                # 每次构建生成的解析报告(不入库)
│   └── tests/                  # pytest 单元测试
└── web/                        # Vue 3 前端
    ├── public/data/            # 管线产出的 JSON(入库,静态部署时无需重跑管线)
    └── src/                    # engine 匹配引擎、stores、views、components
```

## 技术栈

前端:Vue 3、Vite、TypeScript 5.9(不要升级到 7,与 vue-tsc 不兼容)、Element Plus、Pinia、Vitest。界面为「公文纸墨风」:设计变量与 Element Plus 主题覆盖都在 `web/src/style.css`,标题字体为 Noto Serif SC(`@fontsource` 本地打包)。改配色只需改 `style.css` 顶部的 CSS 变量。
数据管线:Python 3(xlrd、openpyxl、pyyaml、pytest)。
架构:管线离线生成 JSON,前端静态托管,匹配在浏览器内完成,用户信息不上传。

## 数据来源与更新

| 数据 | 来源 | 获取方式 |
| --- | --- | --- |
| 国考职位表 | 国家公务员局专题站,2027 年度预计 `http://bm.scs.gov.cn/kl2027`,预计 **2026-10-14** 发布 | **人工下载**《招考简章》xls 放入 `data-pipeline/raw/`。官方下载页有图形验证码,不做自动化绕过。 |
| 专业目录 | 教育部《普通高等学校本科专业目录(2025 年)》、《研究生教育学科专业目录(2022 年)》 | 已整理在 `data-pipeline/catalogs/source/` |
| 浙江、江苏省考职位表 | 各省人社厅或人事考试网 | 二期,人工下载官方附件后解析 |

**开发样本(仅开发使用)**:2026 年度国考职位表第三方镜像 `https://imgbdb4.bendibao.com/excel/2026gwyks.xls`(约 9.9MB,4 个 Sheet,20714 个职位,招录 38119 人,与官方口径一致)。下载到 `data-pipeline/raw/guokao-2026.xls` 即可重新构建。线上数据只使用官方来源。

### 导入 2027 年度职位表(2026-10-14 后)

1. 人工下载 xls,放到 `data-pipeline/raw/guokao-2027.xls`。
2. 修改 `data-pipeline/config/exams.yaml` 的 `guokao-2027`:去掉 `pending: true`,填发布、报名、笔试日期与官方总数,**逐项核对 `ageRule`**(现在是沿用 2026 的占位值,不一定正确)。
3. `.venv/bin/python -m src.build --all`,校验必须通过。
4. `pnpm test && pnpm build`,再抽查结果。

## 注意事项

1. 结果仅供参考,最终以官方公告和招录机关确认为准。
2. 年龄按公告的出生年月区间判断;2026 年度为 18 至 38 周岁(应届硕博 43,公安民警 30),2027 年度以公告为准。
3. 专业、备注是自由文本,解析不了的条件一律标记为「待确认」,不会默认判为符合。
4. 约三分之二的国考职位限应届毕业生,非应届用户可选范围会小很多。
5. 官方发布勘误或补充公告时,重新放入新表并重新构建。

## 维护约定

1. 每完成清单一步,更新方案文档的「Task Progress」和「清单完成状态」,并同步本文件的进度。
2. 新增或修改数据字段时,先改方案文档中的「实现现状与维护指南 / 数据契约」,再改代码。
3. 每年 10 月 14 日前后按上面的流程导入新一年职位表,并核对当年公告中的年龄、学历等公告级规则。
