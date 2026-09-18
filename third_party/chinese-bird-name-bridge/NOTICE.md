# 第三方数据：Chinese-bird-name-bridge（中文鸟名补充包）

本目录下的数据**不是**本项目原创，也不是 eBird 分类数据，来源与授权如下。

## 来源

- 仓库：<https://github.com/Niaoyouji/Chinese-bird-name-bridge>
- 维护者：鸟有记 / Niaoyouji
- 取用版本：`ioc-15.1+wikidata-zh-2026-05-06`（见 JSON 内的 `version` 字段）
- 取用文件：`data/ioc-species-db.json`，**逐字节原样复制，未做任何修改**
  （SHA-256 `67E48DD11E3E873C14E588F82113D4333684F7136B7CF72029F4CCC14DB791CB`，516,784 字节）

## 授权

数据文件按 **CC BY-NC 4.0** 授权，全文见同目录 [LICENSE-DATA](LICENSE-DATA)，来源标注格式：

> Data from Niaoyouji Chinese-bird-name-bridge (CC BY-NC 4.0),
> https://github.com/Niaoyouji/Chinese-bird-name-bridge

上游明确允许「个人 / 学习 / 研究」「开源非商业项目内使用」。本项目以 GPL-3.0 发布且完全免费、
不涉及任何商业化，符合该条件。

⚠️ 注意：
- 该数据**不在 GPL-3.0 的授权范围内**（NC 与 GPL 不兼容），是随包分发的独立授权文件，
  属聚合分发。任何商业用途需另行向上游取得授权。
- 本目录仅随包分发 `ioc-species-db.json` 一个文件。上游 `data/` 下的
  `ebird-zh-overrides.json` 是 eBird 官方简中显示名的演绎，**刻意不取用**，
  以避开本项目「不分发任何 eBird 分类数据及其演绎产物」的合规红线。

## 上游数据来源（转引上游 LICENSE-DATA）

- IOC World Bird List — <https://www.worldbirdnames.org/>（CC BY）
- Wikidata（多语言名上游）— <https://www.wikidata.org/>（CC0）
- Avibase（繁中别名上游）— <https://avibase.bsc-eoc.org/>（CC BY-NC 4.0）
- eBird/Clements Checklist（仅交叉引用）— Cornell Lab of Ornithology
- 《中国鸟类分类与分布名录》第 4 版（郑光美 等编，科学出版社）
- 简中别名兼容层由 Niaoyouji 整理

## 本项目如何使用

建库时按拉丁学名（`sci_name`）与该表的 `latin` 字段精确匹配，把其中的**中文别名与
繁中（台湾 / 香港）名**写入 `taxon_name` 表，供搜索命中；仅在 eBird 未给中文名时，
才用该表的主名回填 `taxon.name_zh`。eBird 提供的主名一律不被覆盖。
