<!--
发布说明模板。发布时**复制成 docs/release-notes/<tag>.md**（例如 v0.1.1.md）并填写——
CI 的发布 job 只认这个路径，文件不存在会直接失败。

约定：
  - {{...}} 形式的是占位符，由 .github/workflows/release.yml 的「渲染发布说明」步骤替换：
      {{VERSION}}         版本号，如 0.1.0
      {{SIZE_SETUP}}      安装包大小（人类可读，如 39.3 MB）
      {{SIZE_PORTABLE}}   免安装包大小
      {{SHA256_SETUP}}    安装包 SHA-256
      {{SHA256_PORTABLE}} 免安装包 SHA-256
      {{SIGNING_STATUS}}  签名状态一句话，由工作流的 SIGNING_ENABLED 开关决定
  - 校验和与体积由 CI 从**即将上传的资产**现算，不要手写、也不要填本地构建的数值。
  - 顶部这段 HTML 注释会在渲染时被自动去掉。
  - 「Code signing policy」段落是 SignPath 对发布页的硬要求，不要删。
  - 发布页固定结构见项目记忆第 3 节。
-->

首个/本版说明一句话：这里是这一版的核心内容。

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-3a7d44) ![License](https://img.shields.io/badge/license-GPL--3.0-3a7d44)

## 功能

（沿用 README 的功能分节；新版本若新增功能，在此补充说明）

## 下载

| 文件 | 说明 |
| --- | --- |
| **`BirdAlbum_Setup_{{VERSION}}.exe`** | **安装版（推荐）**，约 {{SIZE_SETUP}}。安装到 Program Files，可选创建桌面快捷方式，自带卸载项 |
| **`BirdAlbum_{{VERSION}}_portable.zip`** | **免安装版**，约 {{SIZE_PORTABLE}}。解压到任意目录后运行其中的 `鸟类相册.exe` |

## 安装与首次使用

1. 运行安装包（便携版则解压到任意目录）
2. **首次启动会要求导入 eBird 分类表**。出于数据合规要求，程序不随包分发任何 eBird 数据，
   请到康奈尔鸟类学实验室的官方页面免费下载：
   <https://cornell.app.box.com/s/sjci66divvqnz00k98r7pmmb6kpc69zs>
3. 把下载得到的 `eBird_Taxonomy_*.xlsx` 拖入窗口（或点「选择文件」）导入，完成后即可进入程序

## 系统要求

- Windows 10 / 11（64 位）
- 无需安装 Python 或其它运行库，已随包内置
- 首次导入分类表时需要能访问上面的下载地址

## 校验（SHA-256）

```
{{SHA256_SETUP}}  BirdAlbum_Setup_{{VERSION}}.exe
{{SHA256_PORTABLE}}  BirdAlbum_{{VERSION}}_portable.zip
```

> 校验文件内容用。构建机上的原始文件名为 `鸟类相册_Setup_{{VERSION}}.exe` 与
> `鸟类相册_{{VERSION}}_便携版.zip`，与上面的资产内容完全一致
> （发布资产名改为纯 ASCII，避免下载链接出现百分号转义）。

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

- 角色：Authors / Reviewers / Approvers 均为 [@Meartraep](https://github.com/Meartraep)
- 隐私：This program will not transfer any information to other networked systems unless
  specifically requested by the user or the person installing or operating it.
- 每个发布包中的可执行文件由 GitHub Actions 从本仓库源码构建并签名；上游第三方组件
  （PySide6/Pillow/openpyxl 等）保持其原有（未）签名状态，不使用本项目证书签名

## 说明与限制

- {{SIGNING_STATUS}}
- 这是 0.x 早期版本，若后续出现数据结构调整会在发布说明中明确提示
- 分类数据版权归 Cornell Lab of Ornithology（eBird）所有，本程序不附带、也不再分发该数据
- 历史提交：<https://github.com/Meartraep/bird-observation-gallery/commits/main>

## 本版包含的修复

（按条目列出，聚焦「用户能感知到的变化」）

## 技术栈

Python 3.14 · PySide6 6.11 · SQLite · Pillow · openpyxl ｜ 许可证 GPL-3.0
