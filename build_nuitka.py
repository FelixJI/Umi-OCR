#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Nuitka 打包脚本
使用 Nuitka 编译 PySide6 + QML 项目
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "UmiOCR-data"
ABOUT_FILE = DATA_DIR / "about.json"
BUILD_DIR = PROJECT_ROOT / "build_nuitka"
DIST_DIR = PROJECT_ROOT / "dist_nuitka"
TOOLS_7Z = PROJECT_ROOT / "dev-tools" / "7z"


def get_version():
    """从 about.json 读取版本号"""
    with open(ABOUT_FILE, "r", encoding="utf-8") as f:
        about = json.load(f)
    v = about["version"]
    version = f"v{v['major']}.{v['minor']}.{v['patch']}"
    if v["prerelease"]:
        version += f"_{v['prerelease']}"
        if v["prereleaseNumber"]:
            version += f".{v['prereleaseNumber']}"
    return version, about


def create_entry_script(output_path: Path):
    """创建 Nuitka 入口脚本，替代 main.py 的功能"""
    script_content = '''"""
Nuitka 入口脚本
"""
import os
import sys
import site

# 设置工作目录
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(script_dir, "UmiOCR-data")):
    os.chdir(os.path.join(script_dir, "UmiOCR-data"))
else:
    # Nuitka 打包后的目录结构
    os.chdir(script_dir)

# 添加 site-packages 到路径
for n in ["."]:
    path = os.path.abspath(n)
    if os.path.exists(path):
        site.addsitedir(path)

# 设置 QML2_IMPORT_PATH（用于 Qt5Compat）
try:
    import PySide6
    pyside_path = os.path.dirname(PySide6.__file__)
    qml_path = os.path.join(pyside_path, "qml")
    os.environ["QML2_IMPORT_PATH"] = qml_path
except:
    pass

# 启动主程序
from py_src.run import main
main(app_path="", engineAddImportPath=None)
'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    print(f"创建入口脚本: {output_path}")


def build_nuitka(output_dir: Path, plugins: list | None = None, clean: bool = True):
    """
    使用 Nuitka 编译项目

    Args:
        output_dir: 输出目录
        plugins: 要包含的插件列表（如 ['win7_x64_RapidOCR-json']）
        clean: 是否清理之前的构建
    """
    version, about = get_version()

    if clean and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"清理构建目录: {BUILD_DIR}")

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 构建入口点
    entry_script = BUILD_DIR / "nuitka_main.py"
    create_entry_script(entry_script)

    # Nuitka 命令参数
    nuitka_args = [
        sys.executable,
        "-m",
        "Nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        f"--output-dir={output_dir}",
        f"--output-filename=Umi-OCR.exe",
        "--enable-plugin=pyside6",
        "--include-package=PySide6.QtCore",
        "--include-package=PySide6.QtGui",
        "--include-package=PySide6.QtQml",
        "--include-package=PySide6.QtQuick",
        "--include-package=PySide6.QtQuickControls2",
        "--include-package=PySide6.QtWebEngineWidgets",
        "--include-package-data=PySide6",
        "--include-data-files=UmiOCR-data/qt_res=qt_res",
        "--include-data-files=UmiOCR-data/i18n=i18n",
        "--include-data-files=UmiOCR-data/themes.json=themes.json",
        "--include-data-files=UmiOCR-data/about.json=about.json",
        f"--windows-icon-from-ico={DATA_DIR / 'qt_res/images/icons/umiocr.ico'}",
        "--company-name=Umi-OCR",
        f"--product-name={about['name']}",
        f"--file-version={version.replace('v', '').replace('.', ',')}",
        "--file-description=OCR software, free and offline",
        f"--include-data-files=PySide6/Qt6/plugins=plugins",
        f"--include-data-files=PySide6/Qt6/qml=qml",
        "--windows-disable-console",
        "--follow-imports",
        "--include-module=keyboard",
        "--include-module=pymupdf",
        "--include-module=fontTools",
        "--include-module=zxingcpp",
        "--nofollow-module-to=PySide6.Qt3D",
        "--nofollow-module-to=PySide6.QtCharts",
        "--nofollow-module-to=PySide6.QtDataVisualization",
        str(entry_script),
    ]

    # 添加插件
    if plugins:
        for plugin in plugins:
            plugin_path = DATA_DIR / "plugins" / plugin
            if plugin_path.exists():
                nuitka_args.append(
                    f"--include-data-files=UmiOCR-data/plugins/{plugin}=plugins/{plugin}"
                )
                print(f"包含插件: {plugin}")

    print("=== Nuitka 编译 ===")
    print(f"版本: {version}")
    print(f"输出目录: {output_dir}")
    print(f"插件: {plugins if plugins else '无'}")
    print()

    # 执行 Nuitka
    result = subprocess.run(nuitka_args, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("Nuitka 编译失败！")
        return False

    print(f"\n编译完成！输出目录: {output_dir}")
    return True


def copy_additional_files(output_dir: Path, plugins: list | None = None):
    """复制额外文件到输出目录"""
    print("\n=== 复制额外文件 ===")

    # 复制运行脚本（如果存在）
    scripts_to_copy = [
        "RUN_CLI.bat",
        "RUN_GUI.bat",
        "test_speed.bat",
    ]

    for script in scripts_to_copy:
        src = DATA_DIR / script
        if src.exists():
            shutil.copy2(src, output_dir / script)
            print(f"复制: {script}")

    # 复制帮助文件（尝试多种可能的文件名）
    help_files = ["帮助.txt", "Help 帮助.txt"]
    for help_file in help_files:
        src = DATA_DIR / help_file
        if src.exists():
            shutil.copy2(src, output_dir / "帮助.txt")
            print(f"复制: {help_file}")
            break


def package_7z(output_dir: Path, package_name: str, sfx: bool = False):
    """打包成 7z 或自解压 exe"""
    seven_zipr = TOOLS_7Z / "7zr.exe"
    sfx_module = TOOLS_7Z / "7z.sfx"

    # 检查 7z 工具是否存在
    if not seven_zipr.exists():
        print(f"\n警告: 未找到 7zr.exe: {seven_zipr}")
        print("跳过压缩包创建。如需打包，请将 7zr.exe 放置在 {TOOLS_7Z} 目录下。")
        return False

    # 构建 7z 命令
    archive_name = output_dir / package_name
    cmd = [
        str(seven_zipr),
        "a",
        "-mx=7",
        "-t7z",
        f"{archive_name}.7z",
        str(output_dir),
    ]

    print(f"\n=== 创建压缩包 ===")
    print(f"压缩包: {package_name}.7z")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("警告: 7z 压缩失败")
        return False

    # 创建自解压 exe
    if sfx and sfx_module.exists():
        sfx_path = str(sfx_module)
        archive_path = str(archive_name) + ".7z"
        sfx_output = str(archive_name) + ".exe"
        subprocess.run(
            ["cmd", "/c", f'copy /b "{sfx_path}"+"{archive_path}" "{sfx_output}"'],
            shell=True,
            cwd=output_dir,
        )
        print(f"自解压文件: {package_name}.exe")
    elif sfx and not sfx_module.exists():
        print(f"警告: 未找到 7z.sfx: {sfx_module}")
        print("跳过自解压文件创建。")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Umi-OCR Nuitka 打包脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build_nuitka.py              # 完整打包（编译+7z+sfx）
  python build_nuitka.py --no-package  # 只编译，不打包 7z
  python build_nuitka.py --plugins="xxx" # 指定插件打包
        """,
    )
    parser.add_argument(
        "--clean", action="store_true", default=True, help="清理之前的构建"
    )
    parser.add_argument("--no-clean", action="store_true", help="不清理之前的构建")
    parser.add_argument(
        "--package", action="store_true", default=True, help="打包成 7z 压缩包"
    )
    parser.add_argument("--no-package", action="store_true", help="不打包成 7z")
    parser.add_argument(
        "--sfx", action="store_true", default=True, help="创建自解压 exe"
    )
    parser.add_argument("--no-sfx", action="store_true", help="不创建自解压 exe")
    parser.add_argument("--plugins", default="", help="要包含的插件，逗号分隔")
    parser.add_argument(
        "--output", default="./dist_nuitka", help="输出目录（默认: ./dist_nuitka）"
    )

    args = parser.parse_args()

    clean = args.clean and not args.no_clean
    plugins = (
        [p.strip() for p in args.plugins.split(",") if p.strip()]
        if args.plugins
        else []
    )
    output_dir = Path(args.output)

    # 构建
    if not build_nuitka(output_dir, plugins, clean=clean):
        sys.exit(1)

    # 复制额外文件
    copy_additional_files(output_dir, plugins)

    # 打包
    if not args.no_package:
        version, _ = get_version()
        package_name = f"Umi-OCR_{version}"
        package_7z(output_dir, package_name, sfx=(args.sfx and not args.no_sfx))

    print("\n=== 打包完成 ===")


if __name__ == "__main__":
    main()
