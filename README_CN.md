# Generate My Loading Screen 使用说明

这是一个 **Skyrim SE/AE Loading Screen 生成工具**，不是最终游戏模组。

请不要直接把这个工具包安装进 MO2/Vortex。正确流程是：

```text
解压工具包
→ 放入图片
→ 运行脚本
→ 设置 Mod name / ESP filename / Asset folder
→ 安装生成的 output/<你的模组名>.zip
```

## 本版本的 template.nif

本工具包包含一个通用 `template.nif`。  你也可以在第一次运行时指定自己的 2D loading screen 模板 NIF。

## 需要安装

1. Python 3  
   安装时勾选 `Add Python to PATH`。

2. texconv  
   推荐安装命令：

```bat
winget install Microsoft.DirectXTex.Texconv
```

安装后重新打开 CMD，检查：

```bat
where texconv
```

如果脚本找不到 texconv，它会要求你手动粘贴 `texconv.exe` 的完整路径。

## 文件结构

建议这样放：

```text
GenerateMyLoadingScreen/
├─ GenerateMyLoadingScreen_ESL.py
├─ run_GenerateMyLoadingScreen.bat
├─ template.nif
├─ input_16x9/
│  ├─ image01.png
│  ├─ image02.jpg
│  └─ ...
└─ descriptions.csv              ← 第一次运行后自动生成
```

## 图片要求

把图片放入：

```text
input_16x9/
```

支持：

```text
png, jpg, jpeg, webp, bmp, tif, tiff, dds, tga
```

推荐先把图片手动裁剪为 16:9。  
脚本会自动把图片转换为：

```text
2048 × 2048
BC7 DDS
```

这是为了适配当前 2D loading screen 模板 NIF 的显示方式。

## 运行

双击：

```text
run_GenerateMyLoadingScreen.bat
```

第一次运行时会让你设置：

```text
Mod name
ESP filename
Asset folder name
Template NIF path
```

例如：

```text
Mod name: Alice Loading Screens
ESP filename: Alice_LoadingScreens.esp
Asset folder: AliceLoadingScreens
Template NIF path: template.nif
```

配置会保存到：

```text
project_config.json
```

以后再次运行可以直接复用。想重新设置时，删除或编辑 `project_config.json` 即可。

## 文字说明

第一次运行会创建：

```text
descriptions.csv
```

格式如下：

```csv
file,text
image01.png,A quiet moment before the next journey.
image02.jpg,The snow falls silently over Skyrim.
```

`file` 列不要改。  
`text` 列是游戏加载界面显示的文字。

建议使用英文。中文、俄文等文字是否显示正常取决于用户的 Skyrim 字体和本地化环境。

## 输出

脚本会生成：

```text
output/
└─ <Mod name>.zip
```

例如：

```text
output/Alice Loading Screens.zip
```

安装这个生成的 ZIP，而不是安装工具包本身。

生成后的模组结构类似：

```text
Alice Loading Screens.zip
├─ Alice_LoadingScreens.esp       ← ESL-flagged ESP / ESPFE
├─ meshes/
│  └─ AliceLoadingScreens/
│     ├─ 1.nif
│     └─ ...
└─ textures/
   └─ AliceLoadingScreens/
      ├─ 1.dds
      └─ ...
```

## ESL 限制

每张图片生成：

```text
1 个 STAT + 1 个 LSCR
```

因此 ESL compact range 下最多支持：

```text
1024 张图片
```

超过时脚本会停止，避免生成非法 ESL 插件。

## SSEEdit 检查

生成后建议用 SSEEdit 打开生成的 ESP：

1. 右键插件；
2. 选择 `Check for Errors`；
3. 确认 `Errors found: 0`；
4. 检查文件头 `Record Flags` 中有 `ESL`。

## 路径检查

在任意 `STAT` 记录中：

正确：

```text
AssetFolder\1.nif
```

错误：

```text
meshes\AssetFolder\1.nif
```

因为 `STAT -> MODL` 是相对于：

```text
Data\meshes\
```

NIF 内部贴图路径应为：

```text
textures\AssetFolder\1.dds
```
