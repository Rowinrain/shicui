# 拾萃 · 开发说明

高中生物好题本。用户是高中生物老师，用中文交流；回复和界面文字都用中文。

## 结构

- `拾萃.html`：整个程序，单文件（HTML + CSS + JS 都在一个文件里），无依赖、无构建步骤、不联网。修改后直接替换这个文件发布。
- `桌面窗口/`：创建桌面图标的脚本（macOS `.command` 生成 ~/Applications/拾萃.app；Windows `.cmd` 调用 `windows-setup.ps1` 生成快捷方式），都是用 Chrome/Edge 的 `--app=file:///…/拾萃.html` 打开独立窗口，程序本身不变。`.ps1` 必须是 UTF-8 带 BOM、CRLF；`.cmd` 只用 ASCII。
- `tools/word-import/`：Word 题目文档 → 导入 JSON 的 Python 脚本（extract → segment → convert，分节和 tag 写在 mapping.py）。

## 硬性要求

- 数据只存放在用户选定的文件夹（File System Access API），不得读写其他位置；只支持 Chrome / Edge 桌面版。
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
- `notes[]`：`{id, sec, title, body}`；`topics[]`：综合专题；`basket[]`：试题篮。

## 导入与更新文件

- `format: "qbank-import"`：新增题目/笔记/专题（section 可写节编号、节名或 `专题:名称`；tag 可写名字或 `{section, name}`）。
- `format: "qbank-update"`：按 `id` 更新已有题目（tags、addTags、tagsPending、primary、level、grade、review），用于重新打 tag。
- 设置页“导出纯文字版”（`format: "qbank-text"`）可得到不含图片的题目文字，用来整理 tag 后生成 qbank-update 文件。

## 测试

用 Playwright（环境已预装 Chromium）打开 `拾萃.html?demo`（内存中的演示数据，不读写文件夹）；测试真实读写可用 `navigator.storage.getDirectory()` 代替用户文件夹并调用 `useHandle`。
