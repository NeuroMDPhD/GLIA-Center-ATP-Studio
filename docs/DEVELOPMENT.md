# 開発用セットアップ / Developer setup

一般ユーザーはReleasesのWindows ZIPを利用してください。以下はソースを変更する開発者向けです。 / End users should use the Windows ZIP in Releases. The following is for developers modifying source code.

## 必要な環境 / Requirements

- Python 3.12（64 bit） / Python 3.12, 64 bit
- JDK 17（`java`、`javac`、`jar`をPATHに設定） / JDK 17 with `java`, `javac` and `jar` on PATH
- 初回の依存ファイル取得時のみインターネット接続 / Internet for the initial dependency download

## ソースから実行 / Run from source

仮想環境を作成します。 / Create a virtual environment.

```sh
python -m venv .venv
```

Windowsでは次を実行します。 / On Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe scripts/bootstrap_engine.py
.venv\Scripts\python.exe scripts/build_java.py
.venv\Scripts\python.exe launch.py
```

macOSでは次を実行します。 / On macOS:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/bootstrap_engine.py
.venv/bin/python scripts/build_java.py
.venv/bin/python launch.py
```

`bootstrap_engine.py`は`DEPENDENCIES.json`に記録された固定ソースとJARを取得し、SHA-256を照合します。既存のエンジンソースが異なる場合は上書きせず停止します。`vendor/`と`runtime/`はGitの追跡対象外です。Windowsの配布ZIPにはエンジンソース、ライセンス、必要な実行環境を同梱します。

`bootstrap_engine.py` fetches the pinned sources and JARs in `DEPENDENCIES.json` and verifies SHA-256 checksums. It stops rather than overwriting differing existing engine sources. `vendor/` and `runtime/` are not tracked by Git. The Windows distribution includes engine sources, licenses and the necessary runtime.

## テストとマニュアル / Tests and manual

```sh
python -m pytest -q
python scripts/manual_screenshot.py
python scripts/build_manual.py
```

上記の`python`には使用中の仮想環境のPythonを使います。画面例は説明用の架空メタデータから作成し、実験原本を読みません。HTMLと独立したマニュアルZIPを生成します。

Use the virtual environment’s Python in these commands. The screenshot uses illustrative metadata and reads no experimental recordings. The manual build creates HTML and a standalone manual ZIP.

## 配布の構成 / Distribution layout

Windows配布フォルダーには、`python/`にWindows x64のPython 3.12埋め込み版とWindows用依存パッケージ、`runtime/jre/`にWindows x64 Java、`runtime/java-libs/`にビルド済みエンジンが必要です。`python312._pth`には`Lib\site-packages`とアプリルート`..`を設定し、`import site`を有効にします。依存パッケージは`requirements.txt`に固定しています。

The Windows distribution folder needs embedded Windows x64 Python 3.12 and Windows dependency packages in `python/`, Windows x64 Java in `runtime/jre/`, and the built engine in `runtime/java-libs/`. `python312._pth` includes `Lib\site-packages`, app root `..`, and `import site`. Python package versions are pinned in `requirements.txt`.

Zig 0.13.0を用いて、コンソールを表示しないx64ランチャーを作成できます。 / Zig 0.13.0 can build the x64 launcher without a console window.

```sh
python scripts/build_launchers.py --zig /path/to/zig
python scripts/package_windows.py
```

`package_windows.py`は上記の実行環境が事前配置されていることを要求します。Windows実行環境を自動取得するスクリプトではありません。配布物内の`RUNTIME_SOURCES.json`に取得元とチェックサムを記録しています。

`package_windows.py` requires the runtimes to be staged first; it does not download the Windows runtimes automatically. Their sources and checksums are recorded in the distribution’s `RUNTIME_SOURCES.json`.

ZIP内のルート名は`GLIA-ATP`です。このアプリはQt Widgetsを使用するため、未使用の`PySide6/qml/`を配布対象から除外します。元のステージング環境は保持します。WidgetsのDLL・Windowsプラグイン・ライセンスは同梱します。ZIP内のパスがUTF-16で140単位を超えるとビルドを停止します。 / The ZIP root is `GLIA-ATP`. This Qt Widgets app omits unused `PySide6/qml/` assets from the release while preserving the original staging tree. Widgets DLLs, Windows plugins and licenses remain included. Packaging fails if an archive path exceeds 140 UTF-16 code units.

Windows検査用の`python\python.exe scripts\windows_smoke.py C:\GLIA-check\report.json`を配布ルートから実行できます。全ファイルのハッシュ、合成画素の入出力、同梱GUI、JavaおよびFFmpegを確認し、結果と起動画面を保存します。この検査はWindows実機では未実施です。研究データは使用しません。 / A developer can run `python\python.exe scripts\windows_smoke.py C:\GLIA-check\report.json` from the extracted app root on Windows. It checks every file hash, synthetic pixel I/O, the bundled GUI, Java and FFmpeg, then saves a report and startup screenshot. This native Windows check has not yet been executed. No research data is used.

macOSの`--mac`オプションは、そのMacの`.venv`を起動するローカル`.app`を作ります。別のMacへそのまま配れる独立した配布版ではありません。

The `--mac` option creates a local `.app` launcher using that Mac’s `.venv`. It is not a standalone distribution for other Macs.

## 公開時に除外するもの / Publication exclusions

原本OIR/OIB/MAT、プロジェクト、実データの画像、ログ、ローカル検証フォルダー、個別環境パス、認証情報は公開しません。アプリソースと資料はGit、実行パッケージと独立マニュアルはGitHub Releasesで管理します。

Exclude original OIR/OIB/MAT files, projects, real-data images, logs, local QA folders, machine-specific paths and credentials. Keep application sources and documentation in Git; distribute executable packages and the standalone manual through GitHub Releases.
