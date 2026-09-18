# 鸟类相册

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-3a7d44)
![License](https://img.shields.io/badge/license-GPL--3.0-3a7d44)

一个**完全离线**的本地鸟类相册：以 eBird 官方分类体系（目 → 科 → 分类单元）为骨架，
把你拍到的照片挂到对应鸟种下，形成可检索、可积累「成就」的私人鸟类图鉴。

照片、备注、搜索历史全部保存在本机，不上传任何数据。

## 功能

### 分类目录
- **目 → 科 → 分类单元** 三级树，约 1.8 万个分类单元，默认展开到「科」层
- 一键展开/收起全部科；目与科行右侧显示下属数量
- **成就清单**：一键切换为只显示已收录照片的鸟种；完整目录中已收录鸟种以浅粉色标注

### 搜索与直达
- 支持 **中文名 / 英文名 / 拉丁学名 / eBird 代码 / 四字母码** 模糊搜索
- 额外收录第三方补充的中文别名与**繁体**（台湾 / 香港）鸟名，搜「黑鳽」「八色鳥」也能命中对应鸟种
- 全半角括号、中英文空格自动归一化，多词英文名（如 `common kingfisher`）也能命中
- 结果双行显示：第一行为 中文名 + 繁中名（绿色）+ 英文名，第二行为 学名 · 科 · 目；`↑` `↓` 选择、`Enter` 直达并自动展开定位
- 搜索历史自动去重、可一键清空
- 快捷键：`Ctrl+F` 聚焦搜索，`Ctrl+B` 收起/展开左侧目录

### 照片管理
- 按钮多选或**直接把图片拖入**窗口，后台线程复制原图 + 生成缩略图（长边 1000px），界面不卡顿并显示进度
- 支持 `jpg / jpeg / png / webp / bmp / tif / tiff / gif`
- 每张照片可写备注，输入停顿或失焦自动保存
- `↑` `↓` 调整顺序，列表按你的顺序稳定排列
- **SHA-256 判重**：与相册已有照片、以及同一批内的重复都会提示，可选择跳过重复或仍要导入
- 点击缩略图调用系统照片查看器打开原图；原图丢失时给出提示并可打开所在目录

### 存储与数据
- 两种存储方式（切换只影响此后新增的照片）：
  - **全量复制**：原图复制进程序托管目录，源文件移动/删除也不影响查看
  - **引用模式**：只生成缩略图，原图留在你自己的目录里
- 随时在「设置 → 更新数据库」导入新的 eBird 分类表，**已收录照片与搜索历史完整保留**
- 数据位置：`%APPDATA%\BirdAlbum`（`birds.db`、`photos`、`settings.json`），卸载时保留

## 下载与安装

到 [Releases](../../releases) 页下载，两种形式：

| 文件 | 说明 |
| --- | --- |
| `BirdAlbum_Setup_<版本>.exe` | 安装版（推荐）。安装到 Program Files，可选创建桌面快捷方式，自带卸载项 |
| `BirdAlbum_<版本>_portable.zip` | 免安装版。解压到任意目录后运行其中的 `鸟类相册.exe` |

### 首次使用：导入 eBird 分类表

分类骨架（目 → 科 → 分类单元）来自 eBird 官方名录。出于数据合规要求，
**程序不随包分发任何 eBird 分类数据**，所以首次启动会要求导入分类表，
请到康奈尔鸟类学实验室的官方页面免费下载：

<https://cornell.app.box.com/s/zjci66divvqnz00k98r7pmmb6kpc69zs>

把下载得到的 `eBird_Taxonomy_*.xlsx` 拖入窗口（或点「选择文件」）导入，完成后即可进入程序。

> 这一步无法省略：随包带的中文名补充包只提供中文别名与繁中鸟名，
> 不含目、科、分类单元等任何分类层级信息。

## 系统要求

- Windows 10 / 11（64 位）
- 无需安装 Python 或其它运行库，已随包内置
- 首次导入分类表时需要能访问上面的下载地址

## 数据与隐私

- 所有数据都在本机：`%APPDATA%\BirdAlbum`（卸载不删除，便于重装后继续使用）
- 程序**不联网**、无遥测；唯一的网络行为是你在界面上主动点击「打开下载页」/「打开所在目录」时，
  由系统默认浏览器或资源管理器打开对应链接
- 第三方组件：PySide6（Qt，LGPLv3）、Pillow、openpyxl，均不含网络与统计功能
- 随包附带一份第三方的**中文名补充包**（仅中文别名与繁中鸟名，见下面的「许可证」）。它**不是** eBird 数据、
  不含任何分类层级，随包分发不影响 eBird 数据的合规要求

## 从源码构建

需要 Python 3.14（依赖见 `requirements.txt`）：

```powershell
python -m pip install -r requirements.txt

# 主程序（PyInstaller onedir）→ dist\鸟类相册\
python -m PyInstaller BirdAlbum.spec --noconfirm --clean

# 构建后自检：用 offscreen 平台拉起冻结后的 exe，能存活即说明隐藏导入完整
$env:QT_QPA_PLATFORM="offscreen"
$p = Start-Process "dist\鸟类相册\鸟类相册.exe" -PassThru
Start-Sleep -Seconds 10; if (-not $p.HasExited) { $p.Kill() }

# 安装包（Inno Setup 6）与免安装包
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" bird_album.iss
Compress-Archive -Path "dist\鸟类相册" -DestinationPath "installer\鸟类相册_<版本>_便携版.zip"
```

版本号只有一处源头：[app/\_\_init\_\_.py](app/__init__.py) 的 `__version__`；
`bird_album.iss` 的 `MyAppVersion` 需与它保持一致。exe 的 Windows 版本资源由
[tools/make_version_info.py](tools/make_version_info.py) 从该版本号派生，随构建自动写入。

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

> 状态：签名链路正在接入（本项目为单人维护的开源项目，签名由 SignPath Foundation 免费提供）。
> 接入前发布的版本为未签名版本；接入后，发布页上的安装包与免安装包将带有 SignPath Foundation 的 Authenticode 签名。
> 校验发布产物是否来自本仓库：见每次 [Releases](../../releases) 说明中的 SHA-256 校验值，以及
> <https://github.com/Meartraep/bird-observation-gallery/actions> 上的构建记录。

- 角色（本项目为单人维护，三个角色由同一人担任）：
  - Authors（可直接提交到主分支）：[@Meartraep](https://github.com/Meartraep)
  - Reviewers（外部 PR 的审查与合并）：[@Meartraep](https://github.com/Meartraep)
  - Approvers（决定某次发布是否可以被签名）：[@Meartraep](https://github.com/Meartraep)
- 隐私：This program will not transfer any information to other networked systems unless
  specifically requested by the user or the person installing or operating it.
  （详见上面的「数据与隐私」；第三方组件同样不联网）

## 许可证

- 本程序以 [GPL-3.0](LICENSE) 发布（分发时随包附 `LICENSE` 全文）
- eBird 分类数据版权归 Cornell Lab of Ornithology 所有，本程序不附带也不再分发该数据，
  需由使用者从官方地址自行下载导入

### 第三方数据：中文名补充包

随包分发的 `third_party/chinese-bird-name-bridge/` 来自
[Niaoyouji / Chinese-bird-name-bridge](https://github.com/Niaoyouji/Chinese-bird-name-bridge)，
用于补充中文别名与繁中（台湾 / 香港）鸟名。

- **授权：CC BY-NC 4.0**（全文见包内 `LICENSE-DATA`）——**不在本程序 GPL-3.0 的授权范围内**，
  属于独立授权的随包数据。上游明确允许在「个人 / 学习 / 研究」与「开源非商业项目」中使用；
  商业用途需另行取得上游授权
- 署名（依该许可要求）：

  > Data from Niaoyouji Chinese-bird-name-bridge (CC BY-NC 4.0),
  > <https://github.com/Niaoyouji/Chinese-bird-name-bridge>

- 本项目取用的是上游 `data/ioc-species-db.json`，**原样复制、未作修改**；上游
  `data/ebird-zh-overrides.json` 等 eBird 演绎数据**刻意不取用**
- 上游数据来源：IOC World Bird List（CC BY）、Wikidata（CC0）、Avibase（CC BY-NC 4.0）、
  《中国鸟类分类与分布名录》第 4 版（郑光美 等编）
- 详见包内 [`third_party/chinese-bird-name-bridge/NOTICE.md`](third_party/chinese-bird-name-bridge/NOTICE.md)
