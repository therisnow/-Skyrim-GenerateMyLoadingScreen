from __future__ import annotations

import csv
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

# ============================================================
# Generate My Loading Screen - ESL Builder
#
# This is a shareable customizable version.
# It includes a generic template.nif with visible third-party author/mod strings removed.
# Users can also provide their own legal 2D loading screen template NIF.
#
# User-configurable:
#   - Mod name / output folder / ZIP name
#   - ESP filename
#   - Asset folder name under meshes/ and textures/
#   - Template NIF path
#
# Generated structure:
#   <ModName>.zip
#   ├─ <EspName>.esp                         ESL-flagged ESP / ESPFE
#   ├─ meshes/<AssetFolder>/1.nif ...
#   └─ textures/<AssetFolder>/1.dds ...
#
# Correct path rules:
#   STAT -> MODL: <AssetFolder>\1.nif
#   NIF texture path: textures\<AssetFolder>\1.dds
# ============================================================

DEFAULT_MOD_NAME = "My_LoadingScreens"
DEFAULT_ESP_NAME = "My_LoadingScreens.esp"
DEFAULT_ASSET_FOLDER = "MyLoadingScreens"

INPUT_DIR_NAME = "input_16x9"
OUTPUT_DIR_NAME = "output"
CONFIG_NAME = "project_config.json"
DESCRIPTIONS_CSV_NAME = "descriptions.csv"
DEFAULT_TEXT = "Custom loading screen."

START_INDEX = 1
DIGITS = 0  # 0 -> 1.dds, 2.dds; 3 -> 001.dds, 002.dds

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".dds", ".tga"}

# ESL compact range.
# This script creates 1 LSCR + 1 STAT for each image.
LSCR_BASE_ID = 0x00000800
ESL_FLAG = 0x00000200
ESL_MAX_LOCAL_ID = 0x00000FFF


# ============================================================
# Utility
# ============================================================

def script_dir() -> Path:
    return Path(__file__).resolve().parent


def pause(msg: str = "Press Enter to continue...") -> None:
    try:
        input(msg)
    except EOFError:
        pass


def ask_text(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def safe_windows_filename(name: str, default: str) -> str:
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = default
    return name


def safe_asset_folder(name: str, default: str) -> str:
    # Keep it simple and highly compatible for NIF/ESP paths.
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        name = default
    return name


def clean_editor_id(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "LoadingScreens"
    if not s[0].isalpha():
        s = "LS_" + s
    return s[:80]


def game_path_to_os_path(game_path: str) -> Path:
    return Path(game_path.replace("\\", os.sep))


def numbered_name(i: int, ext: str) -> str:
    if DIGITS and DIGITS > 0:
        return f"{i:0{DIGITS}d}{ext}"
    return f"{i}{ext}"


# ============================================================
# Project configuration
# ============================================================

def create_or_load_config() -> dict:
    here = script_dir()
    cfg_path = here / CONFIG_NAME

    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            print("[Config] Existing project_config.json found:")
            print(f"  Mod name:      {cfg.get('mod_name', '')}")
            print(f"  ESP filename:  {cfg.get('esp_name', '')}")
            print(f"  Asset folder:  {cfg.get('asset_folder', '')}")
            print(f"  Template NIF:  {cfg.get('template_nif', '')}")
            print()
            ans = input("Use this config? [Y/N/Edit] ").strip().lower()
            if ans in ("", "y", "yes"):
                return validate_config(cfg)
        except Exception as exc:
            print(f"[Warning] Cannot read existing config: {exc}")
            print("A new config will be created.")
            print()

    print("Create project config.")
    print()

    mod_name = safe_windows_filename(
        ask_text("Mod name / output ZIP folder name", DEFAULT_MOD_NAME),
        DEFAULT_MOD_NAME,
    )

    default_esp = mod_name
    if not default_esp.lower().endswith(".esp"):
        default_esp += ".esp"
    esp_name = safe_windows_filename(
        ask_text("ESP filename", default_esp),
        DEFAULT_ESP_NAME,
    )
    if not esp_name.lower().endswith(".esp"):
        esp_name += ".esp"

    default_asset = safe_asset_folder(Path(esp_name).stem, DEFAULT_ASSET_FOLDER)
    asset_folder = safe_asset_folder(
        ask_text("Asset folder name under meshes/ and textures/", default_asset),
        DEFAULT_ASSET_FOLDER,
    )

    default_template = "template.nif"
    template_nif = input(
        f"Template NIF path [{default_template}] "
        "(leave empty to use the included template.nif): "
    ).strip().strip('"')
    if not template_nif:
        template_nif = default_template

    cfg = {
        "mod_name": mod_name,
        "esp_name": esp_name,
        "asset_folder": asset_folder,
        "template_nif": template_nif,
    }

    cfg = validate_config(cfg)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"[Config] Saved: {cfg_path}")
    print()
    return cfg


def validate_config(cfg: dict) -> dict:
    mod_name = safe_windows_filename(str(cfg.get("mod_name", DEFAULT_MOD_NAME)), DEFAULT_MOD_NAME)
    esp_name = safe_windows_filename(str(cfg.get("esp_name", DEFAULT_ESP_NAME)), DEFAULT_ESP_NAME)
    if not esp_name.lower().endswith(".esp"):
        esp_name += ".esp"
    asset_folder = safe_asset_folder(str(cfg.get("asset_folder", DEFAULT_ASSET_FOLDER)), DEFAULT_ASSET_FOLDER)
    template_nif = str(cfg.get("template_nif", "template.nif")).strip().strip('"') or "template.nif"

    return {
        "mod_name": mod_name,
        "esp_name": esp_name,
        "asset_folder": asset_folder,
        "template_nif": template_nif,
    }


def resolve_template_path(template_value: str) -> Path:
    p = Path(template_value).expanduser()
    if not p.is_absolute():
        p = script_dir() / p
    p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(
            "Template NIF was not found.\n"
            f"Expected: {p}\n\n"
            "The default template.nif was not found.\n"
            "Place a 2D loading screen template NIF next to the script and name it template.nif,\n"
            "or edit project_config.json and set template_nif to the correct path."
        )
    return p


# ============================================================
# texconv discovery
# ============================================================

def find_texconv() -> Optional[Path]:
    here = script_dir()
    candidates: list[Path] = [here / "texconv.exe", here / "texconv"]

    for name in ("texconv.exe", "texconv"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    local = os.environ.get("LOCALAPPDATA")
    if local:
        packages = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if packages.exists():
            try:
                for p in packages.rglob("texconv.exe"):
                    if p.is_file():
                        candidates.append(p)
            except Exception:
                pass

    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c.resolve()
        except Exception:
            pass

    return None


def ask_texconv_path() -> Path:
    texconv = find_texconv()
    if texconv:
        print(f"[OK] texconv found: {texconv}")
        return texconv

    print("[ERROR] texconv was not found automatically.")
    print()
    print("Install it with:")
    print("  winget install Microsoft.DirectXTex.Texconv")
    print()
    print("Then close this window, open a new CMD, and test:")
    print("  where texconv")
    print()
    value = input("Full texconv.exe path, or empty to abort: ").strip().strip('"')
    if not value:
        raise RuntimeError("texconv.exe is required.")
    p = Path(value).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"texconv.exe not found: {p}")
    return p


# ============================================================
# Input images + descriptions
# ============================================================

def scan_images(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Created] {input_dir}")
        print("Put your manually cropped 16:9 images into this folder and run again.")
        pause()
        sys.exit(0)

    imgs = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    imgs.sort(key=lambda p: p.name.lower())
    return imgs


def ensure_descriptions_csv(images: list[Path], csv_path: Path) -> dict[str, str]:
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "text"])
            for img in images:
                writer.writerow([img.name, DEFAULT_TEXT])

        print(f"[Created] {csv_path.name}")
        print("Open descriptions.csv, edit the text column, save it, then return here.")
        print()
        print("Example:")
        print("  file,text")
        print("  1.png,A quiet moment before the next journey.")
        print()
        pause("After editing descriptions.csv, press Enter to continue...")

    result: dict[str, str] = {}
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "file" not in reader.fieldnames or "text" not in reader.fieldnames:
            raise RuntimeError("descriptions.csv must have columns: file,text")
        for row in reader:
            filename = (row.get("file") or "").strip()
            text = (row.get("text") or "").strip()
            if filename:
                result[filename] = text if text else DEFAULT_TEXT

    missing = [img for img in images if img.name not in result]
    if missing:
        with csv_path.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            for img in missing:
                writer.writerow([img.name, DEFAULT_TEXT])
                result[img.name] = DEFAULT_TEXT
        print(f"[Info] Added {len(missing)} new image(s) to descriptions.csv.")
        pause("Edit descriptions.csv if needed, then press Enter to continue...")

    return result


# ============================================================
# DDS conversion
# ============================================================

def convert_to_dds(texconv: Path, src: Path, out_dds: Path) -> None:
    out_dds.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        cmd = [
            str(texconv),
            "-y",
            "-f", "BC7_UNORM",
            "-m", "0",
            "-w", "2048",
            "-h", "2048",
            "-o", str(tmp),
            str(src),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        if proc.returncode != 0:
            print("[texconv stdout]")
            print(proc.stdout)
            print("[texconv stderr]")
            print(proc.stderr)
            raise RuntimeError(f"texconv failed on: {src.name}")

        dds_files = list(tmp.glob("*.dds")) + list(tmp.glob("*.DDS"))
        if not dds_files:
            print(proc.stdout)
            print(proc.stderr)
            raise RuntimeError(f"texconv did not create a DDS file for: {src.name}")

        generated = dds_files[0]
        if out_dds.exists():
            out_dds.unlink()
        shutil.move(str(generated), str(out_dds))


# ============================================================
# NIF patching
# ============================================================

def find_first_dds_path_in_nif(data: bytes) -> tuple[int, int, bytes]:
    """
    Return (length_prefix_pos, path_start_pos, old_path_bytes).

    The known working 2D loading screen template stores texture paths
    as uint32 length + ASCII bytes.
    """
    pattern = re.compile(rb"(?i)textures\\[^\x00]+?\.dds")
    matches = list(pattern.finditer(data))
    if not matches:
        raise RuntimeError(
            "No DDS path found in template NIF.\n"
            "Open the NIF in NifSkope and make sure it contains a texture path like:\n"
            "textures\\SomeFolder\\SomeFile.dds"
        )

    for m in matches:
        start = m.start()
        old_path = m.group(0)
        if start >= 4:
            length_pos = start - 4
            stored_len = struct.unpack("<I", data[length_pos:start])[0]
            if stored_len == len(old_path):
                return length_pos, start, old_path

    m = matches[0]
    raise RuntimeError(
        "DDS path found, but the NIF string length prefix was not identified.\n"
        f"Found path: {m.group(0).decode('ascii', errors='replace')}\n\n"
        "This template NIF uses an unsupported string layout."
    )


def patch_nif_texture_path(template_nif: Path, output_nif: Path, new_texture_path: str) -> None:
    data = template_nif.read_bytes()
    length_pos, path_start, old_path = find_first_dds_path_in_nif(data)
    old_len = len(old_path)
    old_chunk_end = path_start + old_len

    new_path = new_texture_path.encode("ascii")
    new_chunk = struct.pack("<I", len(new_path)) + new_path

    patched = data[:length_pos] + new_chunk + data[old_chunk_end:]
    output_nif.parent.mkdir(parents=True, exist_ok=True)
    output_nif.write_bytes(patched)


# ============================================================
# ESP writer
# ============================================================

def zstring(text: str) -> bytes:
    # English is safest for public releases. UTF-8 may display in xEdit,
    # but in-game font support depends on the user's localization.
    return text.encode("utf-8", errors="replace") + b"\x00"


def subrecord(sig: str, data: bytes) -> bytes:
    if len(sig) != 4:
        raise ValueError(sig)
    if len(data) > 65535:
        raise ValueError(f"Subrecord too large: {sig}")
    return sig.encode("ascii") + struct.pack("<H", len(data)) + data


def record(sig: str, data: bytes, form_id: int, flags: int = 0, form_version: int = 44) -> bytes:
    return (
        sig.encode("ascii")
        + struct.pack("<I", len(data))
        + struct.pack("<I", flags)
        + struct.pack("<I", form_id)
        + struct.pack("<I", 0)
        + struct.pack("<H", form_version)
        + struct.pack("<H", 0)
        + data
    )


def group(top_signature: str, records: list[bytes]) -> bytes:
    body = b"".join(records)
    return (
        b"GRUP"
        + struct.pack("<I", 24 + len(body))
        + top_signature.encode("ascii")
        + struct.pack("<i", 0)
        + struct.pack("<H", 0)
        + struct.pack("<H", 0)
        + struct.pack("<I", 0)
        + body
    )


def make_tes4_record(total_records: int, next_object_id: int) -> bytes:
    data = b""
    data += subrecord("HEDR", struct.pack("<fII", 1.7, total_records + 2, next_object_id))
    data += subrecord("CNAM", zstring("DEFAULT"))
    data += subrecord("INTV", struct.pack("<I", 1))

    # ESL flag for ESPFE / ESL-flagged ESP.
    return record("TES4", data, 0x00000000, flags=ESL_FLAG, form_version=44)


def make_stat_record(form_id: int, editor_id: str, model_path_for_modl: str) -> bytes:
    data = b""
    data += subrecord("EDID", zstring(editor_id))
    data += subrecord("OBND", struct.pack("<hhhhhh", 0, 0, 0, 0, 0, 0))

    # Critical:
    # MODL is relative to Data\meshes.
    # Correct: AssetFolder\1.nif
    # Wrong:   meshes\AssetFolder\1.nif
    data += subrecord("MODL", zstring(model_path_for_modl))

    # Reference-style STAT layout.
    data += subrecord("MODT", bytes.fromhex("020000000000000000000000"))
    data += subrecord("DNAM", bytes.fromhex("0000b4420000000000000000"))
    return record("STAT", data, form_id, flags=0, form_version=44)


def make_lscr_record(form_id: int, editor_id: str, displayed_text: str, stat_form_id: int) -> bytes:
    data = b""
    data += subrecord("EDID", zstring(editor_id))
    data += subrecord("DESC", zstring(displayed_text))

    # Reference-style always-eligible condition.
    data += subrecord("CTDA", bytes.fromhex("a00000000000c8424d00000000000000000000000000000000000000ffffffff"))

    data += subrecord("NNAM", struct.pack("<I", stat_form_id))
    data += subrecord("SNAM", struct.pack("<f", 2.0))
    data += subrecord("RNAM", struct.pack("<hhh", -90, 0, 0))
    data += subrecord("ONAM", struct.pack("<hh", 0, 0))
    data += subrecord("XNAM", bytes.fromhex("000034c20000000000000000"))
    return record("LSCR", data, form_id, flags=0, form_version=44)


def build_esp(esp_path: Path, entries: list[dict], edid_prefix: str) -> None:
    n = len(entries)
    if n <= 0:
        raise RuntimeError("No images / entries to write.")

    highest_local_id = LSCR_BASE_ID + 2 * n - 1
    if highest_local_id > ESL_MAX_LOCAL_ID:
        raise RuntimeError(
            "Too many images for ESL-flagged ESP.\n"
            f"Images: {n}\n"
            f"Highest generated local FormID would be 0x{highest_local_id:06X}, "
            f"but ESL compact range ends at 0x{ESL_MAX_LOCAL_ID:06X}.\n"
            "Limit: 1024 images, because each image creates 1 STAT + 1 LSCR."
        )

    stat_base_id = LSCR_BASE_ID + n

    stat_records = []
    lscr_records = []

    edid_prefix = clean_editor_id(edid_prefix)

    for i, entry in enumerate(entries):
        idx = entry["index"]
        stat_form_id = stat_base_id + i
        lscr_form_id = LSCR_BASE_ID + i

        stat_edid = clean_editor_id(f"{edid_prefix}_STAT_{idx:03d}")
        lscr_edid = clean_editor_id(f"{edid_prefix}_LSCR_{idx:03d}")

        stat_records.append(make_stat_record(stat_form_id, stat_edid, entry["mesh_modl_path"]))
        lscr_records.append(make_lscr_record(lscr_form_id, lscr_edid, entry["text"], stat_form_id))

    total_records = len(stat_records) + len(lscr_records)
    next_object_id = LSCR_BASE_ID + total_records + 1

    data = b""
    data += make_tes4_record(total_records, next_object_id)
    data += group("STAT", stat_records)
    data += group("LSCR", lscr_records)

    esp_path.write_bytes(data)


# ============================================================
# ZIP
# ============================================================

def make_zip(mod_folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in mod_folder.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(mod_folder).as_posix())


# ============================================================
# Main
# ============================================================

def main() -> None:
    here = script_dir()
    input_dir = here / INPUT_DIR_NAME
    descriptions_csv = here / DESCRIPTIONS_CSV_NAME
    output_root = here / OUTPUT_DIR_NAME

    print("====================================================")
    print(" Generate My Loading Screen - ESL Builder")
    print("====================================================")
    print()
    print("This is a generator tool, not the final Skyrim mod.")
    print("Run this script first, then install the generated ZIP.")
    print()
    print("This package includes a generic template.nif.")
    print("You can also provide your own 2D loading screen template NIF if needed.")
    print()

    cfg = create_or_load_config()

    mod_name = cfg["mod_name"]
    esp_name = cfg["esp_name"]
    asset_folder = cfg["asset_folder"]
    template_nif = resolve_template_path(cfg["template_nif"])

    mesh_folder_data = rf"meshes\{asset_folder}"
    texture_folder_data = rf"textures\{asset_folder}"
    mesh_folder_modl = asset_folder
    texture_folder_nif = rf"textures\{asset_folder}"

    mod_folder = output_root / mod_name
    zip_path = output_root / f"{mod_name}.zip"

    images = scan_images(input_dir)
    if not images:
        print(f"[ERROR] No images found in {input_dir}")
        print("Supported: png, jpg, jpeg, webp, bmp, tif, tiff, dds, tga")
        pause()
        return

    descriptions = ensure_descriptions_csv(images, descriptions_csv)
    texconv = ask_texconv_path()

    print()
    print("Project:")
    print(f"  Mod name:      {mod_name}")
    print(f"  ESP filename:  {esp_name}")
    print(f"  Asset folder:  {asset_folder}")
    print(f"  Template NIF:  {template_nif}")
    print()
    print(f"Images:          {len(images)}")
    print("ESP type:        ESL-flagged ESP / ESPFE")
    print(f"Output ZIP:      {zip_path}")
    print()

    ans = input("Build now? [Y/N] ").strip().lower()
    if ans not in ("", "y", "yes"):
        print("Cancelled.")
        return

    if mod_folder.exists():
        shutil.rmtree(mod_folder)
    mod_folder.mkdir(parents=True, exist_ok=True)

    textures_dir = mod_folder / game_path_to_os_path(texture_folder_data)
    meshes_dir = mod_folder / game_path_to_os_path(mesh_folder_data)
    textures_dir.mkdir(parents=True, exist_ok=True)
    meshes_dir.mkdir(parents=True, exist_ok=True)

    entries = []

    print()
    print("[1/4] Converting images to 2048x2048 BC7 DDS and patching NIFs...")
    for n, src in enumerate(images, start=START_INDEX):
        dds_name = numbered_name(n, ".dds")
        nif_name = numbered_name(n, ".nif")

        target_dds = textures_dir / dds_name
        target_nif = meshes_dir / nif_name

        texture_path_in_nif = rf"{texture_folder_nif}\{dds_name}"
        mesh_path_for_modl = rf"{mesh_folder_modl}\{nif_name}"

        print(f"  {src.name} -> {dds_name}, {nif_name}")

        convert_to_dds(texconv, src, target_dds)
        patch_nif_texture_path(template_nif, target_nif, texture_path_in_nif)

        entries.append({
            "index": n,
            "source_file": src.name,
            "text": descriptions.get(src.name, DEFAULT_TEXT),
            "mesh_modl_path": mesh_path_for_modl,
            "texture_nif_path": texture_path_in_nif,
        })

    print("[2/4] Generating ESL-flagged ESP...")
    build_esp(mod_folder / esp_name, entries, edid_prefix=Path(esp_name).stem)

    print("[3/4] Writing README and used descriptions...")
    with (mod_folder / "README.txt").open("w", encoding="utf-8") as f:
        f.write(
            f"{mod_name}\n"
            f"{'=' * len(mod_name)}\n\n"
            "Generated Skyrim SE/AE loading screen mod.\n\n"
            "This plugin is ESL-flagged / ESPFE.\n"
            "It should not take a normal ESP plugin slot.\n\n"
            "Generated structure:\n"
            f"  - {esp_name}\n"
            f"  - meshes\\{asset_folder}\\1.nif ...\n"
            f"  - textures\\{asset_folder}\\1.dds ...\n\n"
            "Recommended check:\n"
            "  Open the ESP in SSEEdit and run Check for Errors.\n"
            "  The file header should show the ESL flag.\n"
        )

    with (mod_folder / "descriptions_used.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["source_file", "generated_index", "text", "stat_modl_mesh", "nif_texture"])
        for e in entries:
            writer.writerow([e["source_file"], e["index"], e["text"], e["mesh_modl_path"], e["texture_nif_path"]])

    with (mod_folder / "project_config_used.json").open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print("[4/4] Packing ZIP...")
    output_root.mkdir(parents=True, exist_ok=True)
    make_zip(mod_folder, zip_path)

    print()
    print("DONE")
    print(f"Mod folder: {mod_folder}")
    print(f"ZIP file:   {zip_path}")
    print()
    print("Install the generated ZIP with MO2/Vortex.")
    print("Do NOT install this generator folder as the final mod.")
    print()
    pause()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("ERROR")
        print(exc)
        print()
        pause()
        raise
