# 拾萃 · 开发说明

高中生物好题本。用户是高中生物老师，用中文交流；回复和界面文字都用中文。

## 结构

- `拾萃.html`：整个程序，单文件（HTML + CSS + JS 都在一个文件里），无依赖、无构建步骤，只在检查更新时联网。修改后直接替换这个文件发布。
- `latest.json` / `更新记录.md` / `tools/release.py`：在线更新（见下）。
- `tools/word-import/`：Word 题目文档 → 导入 JSON 的 Python 脚本（extract → segment → convert，分节和 tag 写在 mapping.py）。

## 硬性要求

- 数据只存放在用户选定的文件夹（File System Access API），不得读写其他位置；唯一例外是在线更新时写入用户选中的 拾萃.html。只支持 Chrome / Edge 桌面版。
- 只有检查更新时联网（用户手动点“检查更新”，或打开后自动检查：延迟几秒、之后每 6 小时，只读 latest.json，设置 `settings.autoUpdate=false` 可关；`?demo` 下默认不查，加 `&autoupdate` 才查）。不要加其他联网功能，自动检查也不能自动下载或安装。
- 界面里任何地方都不要提到 Claude、AI 等，只写基础操作说明。
- 题干里不显示答案：选择/判断题末尾显示空的（　　），填空显示空白下划线；答案、曾选错/判错/答错的标记只出现在答案区。
- 曾做错的题，难度默认归为“较难”（用户手动选过难度则不改）。
- 新版必须能读旧数据：`normQ` / `normalizeBank` 负责补默认值和迁移；改数据格式时提升 `APP_VERSION`，升级前会自动备份到 backups/。
- 仓库是公开的：不要提交任何题目数据（bank.json、images、导入 JSON、检查明细）。

## 数据格式要点（bank.json）

- `questions[]`：`type` 为 judge / single / multi / fill / answer / exp；`stem`、`options`、`analysis`、`extra`（补充）、`note`（备注）为 HTML。
  - 选择题 `key` 为答案字母，`wrong` 为曾选错的字母（误选或漏选）。
  - 判断题 `judges: [{text, key: '✓'|'×', miss}]`，`stem` 为可选的共同题干。
  - 题干末尾的（　）占位：`<span class="ans-slot"></span>`（见 `ensureSlot`）。
  - 填空：`<u class="blank">答案</u>`，答错为 `<u class="blank miss">`。
  - `primary` 为主节编号“书-章-节”（综合专题为 `Z-0-<id>`），`tags` 为 tag id；`tagsPending`、`levelUnset`、`review`（导入备注）、`missed`、`grade`（高一/高二/高三）、`source`、`qno`、`adapted`。
- `tags[]`：`{id, sec, name}`，每节独立的 tag 库；题目借用其他节的 tag 即算跨节。
- `notes[]`：`{id, sec, title, body}`；`topics[]`：综合专题；`basket[]`：试题篮 `{qid, score, subScores?}`。
- `papers[]`：保存的试卷 `{id, name, date, entries}`（entries 同 basket），题目“已用于几份试卷”由它统计；`basketPaper` 为试题篮当前对应的试卷 id。
- `exams[]`：整卷 `{id, name, grade, date, note, items}`，`items` 按原卷顺序，元素是大题标题 `{id, kind: 'head', text}` 或题目（字段同 questions，另有 `qid`＝收进题库后题库里那道题的 id）。整卷里的题不在 `questions` 里，不参与搜索、目录计数和查重；“收进题库”是复制一份。
- `trash[]`：回收站 `{kind: 'q'|'n'|'e', deleted, item}`，打开时清除超过 30 天的；清理图片时也算作在用。
- `settings.print`：上次的导出试卷选项（版式、答案位置、纸张等，旧版的 `content` 会自动换算成 `ans`）。

## 导入与更新文件

- `format: "qbank-import"`：新增题目/笔记/专题（section 可写节编号、节名或 `专题:名称`；tag 可写名字或 `{section, name}`）。
- `format: "qbank-exam"`：新建一份整卷 `{name, grade, date, items}`，items 里写 `{head: "一、单项选择题"}`（或直接写字符串）表示大题标题，其余同 qbank-import 的题目（section、tags 可不写）。在整卷页面里也可以把 qbank-import 文件的题按顺序导入整卷。
- `format: "qbank-update"`：按 `id` 更新已有题目（tags、addTags、tagsPending、primary、level、grade、review），用于重新打 tag。
- 设置页“导出纯文字版”（`format: "qbank-text"`）可得到不含图片的题目文字，用来整理 tag 后生成 qbank-update 文件。

## 发布新版（在线更新）

程序内“设置 → 程序更新”读取 main 分支上的 `latest.json`（raw.githubusercontent.com，连不上时用 jsDelivr 和 ghfast.top 等加速地址，需两个来源一致），下载 拾萃.html 并按 sha256 校验后写入用户选中的 拾萃.html（句柄存在 IndexedDB `program`），旧版备份到 backups/。所以**合并到 main 就是发布**：

1. 改 拾萃.html 时把 `PROGRAM_VERSION` 改大（只改了说明文档可以不改）；数据格式变了另外提升 `APP_VERSION`。
   - 版本号规则（用户定的）：v1.x 是加入在线更新以前的版本，v2.x 起有在线更新。极小的改动只改最后一位（2.7.0 → 2.7.1），小功能更新改中间一位（2.7.0 → 2.8.0），只有重大更新才改第一位（v3.0.0），以此类推。
   - 兼容旧编号：v2.1.0–v2.6.0 当时编号为 3.1.0–3.6.0，它们的更新程序读 latest.json 的 `version`，并核对下载文件里第一个 `const PROGRAM_VERSION='…'`。所以 latest.json 的 `version` 和 拾萃.html 里 `兼容旧版更新：const PROGRAM_VERSION='…'` 注释都写“第一位加 1”的旧编号，真正的版本号在 `release` 字段；release.py 会自动改好，不要删那行注释。程序内比较版本一律用 `release`，`programVersionOf` 把没有该注释的旧文件 3.x 换算成 2.x。
2. 在 `更新记录.md` 顶部加 `## v新版本号` 和更新内容（用户会在更新提示里看到）。
3. 运行 `python3 tools/release.py` 重新生成 latest.json，一起提交。GitHub Actions 会用 `--check` 检查三者是否一致；拾萃.html 改了但 latest.json 没重新生成，用户更新时 sha256 会校验失败。
4. 顺带更新 `README.md`（使用说明，面向第一次下载的人：下载、用 Chrome 打开、选数据文件夹、主要功能、更新）。在线更新只替换 拾萃.html，不会改动用户本地的说明，这是有意的。

## 测试

用 Playwright（环境已预装 Chromium）打开 `拾萃.html?demo`（内存中的演示数据，不读写文件夹）；测试真实读写可用 `navigator.storage.getDirectory()` 代替用户文件夹并调用 `useHandle`。

测试在线更新：用 `page.route` 拦截 raw.githubusercontent.com / jsdelivr / 加速地址，返回伪造的 latest.json 和改了版本号的 拾萃.html；程序文件用 OPFS 里的文件代替。注意 headless Chromium 从 IndexedDB 读回 OPFS 句柄会崩溃，测试时要把 `idbGet('program')` 换成直接返回句柄。
