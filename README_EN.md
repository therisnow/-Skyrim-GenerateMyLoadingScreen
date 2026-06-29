# Generate My Loading Screen User Guide

This is a **Skyrim SE/AE loading screen generator tool**, not the final in-game mod.

Do not install this generator folder directly with MO2/Vortex. The correct workflow is:

```text
Extract this tool
→ add your images
→ run the script
→ set Mod name / ESP filename / Asset folder
→ install the generated output/<Your Mod Name>.zip
```

## About template.nif

This package includes a generic `template.nif`.  You can also provide your own 2D loading screen template NIF during the first run.

## Requirements

1. Python 3  
   Enable `Add Python to PATH` during installation.

2. texconv  
   Recommended installation command:

```bat
winget install Microsoft.DirectXTex.Texconv
```

After installation, open a new CMD window and check:

```bat
where texconv
```

If the script cannot find texconv, it will ask you to paste the full path to `texconv.exe`.

## Folder Layout

Recommended layout:

```text
GenerateMyLoadingScreen/
├─ GenerateMyLoadingScreen_ESL.py
├─ run_GenerateMyLoadingScreen.bat
├─ template.nif
├─ input_16x9/
│  ├─ image01.png
│  ├─ image02.jpg
│  └─ ...
└─ descriptions.csv              ← auto-created on first run
```

## Image Preparation

Place your images in:

```text
input_16x9/
```

Supported formats:

```text
png, jpg, jpeg, webp, bmp, tif, tiff, dds, tga
```

It is recommended to manually crop your images to 16:9 first.  
The script converts them to:

```text
2048 × 2048
BC7 DDS
```

This matches the behavior of the included 2D loading screen template NIF.

## Running the Script

Double-click:

```text
run_GenerateMyLoadingScreen.bat
```

On the first run, the script asks for:

```text
Mod name
ESP filename
Asset folder name
Template NIF path
```

Example:

```text
Mod name: Alice Loading Screens
ESP filename: Alice_LoadingScreens.esp
Asset folder: AliceLoadingScreens
Template NIF path: template.nif
```

The configuration is saved to:

```text
project_config.json
```

Future runs can reuse the same config. To reset the settings, delete or edit `project_config.json`.

## Loading Screen Text

On first run, the script creates:

```text
descriptions.csv
```

Example:

```csv
file,text
image01.png,A quiet moment before the next journey.
image02.jpg,The snow falls silently over Skyrim.
```

Do not change the `file` column.  
The `text` column is displayed on the loading screen.

English text is recommended. Chinese, Russian, or other languages depend on the user's Skyrim font and localization setup.

## Output

The script generates:

```text
output/
└─ <Mod name>.zip
```

Example:

```text
output/Alice Loading Screens.zip
```

Install this generated ZIP, not the generator folder itself.

The generated mod looks like:

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

## ESL Limit

Each image creates:

```text
1 STAT + 1 LSCR
```

So the ESL compact range supports up to:

```text
1024 images
```

If the limit is exceeded, the script stops instead of generating an invalid ESL plugin.

## SSEEdit Check

After generation, open the generated ESP in SSEEdit:

1. Right-click the plugin;
2. choose `Check for Errors`;
3. confirm `Errors found: 0`;
4. check that the file header `Record Flags` contains `ESL`.

## Path Check

In any generated `STAT` record:

Correct:

```text
AssetFolder\1.nif
```

Wrong:

```text
meshes\AssetFolder\1.nif
```

`STAT -> MODL` is relative to:

```text
Data\meshes\
```

The texture path inside the NIF should be:

```text
textures\AssetFolder\1.dds
```

## Note

This tool follows the reference-mod style: it adds new loading screen records instead of deleting vanilla ones.  
The more images you add, the more often your custom loading screens will appear.
