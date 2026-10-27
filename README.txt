GLIA Center ATP Studio 0.2.2 — Research preview / 研究用プレビュー

Windows portable package / Windowsポータブル版
  dist/GLIA-Center-ATP-Studio-Windows-x64.zip
  Extract the whole archive, then double-click GLIA Center ATP Studio.exe (GLIA logo).
  ZIP全体を展開し、GLIAロゴのGLIA Center ATP Studio.exeをダブルクリックしてください。
  Keep the executable with its accompanying folders; no setup or commands are needed.
  実行ファイルを同梱フォルダーと一緒に保存してください。セットアップやコマンド入力は不要です。
  MATLAB, Fiji and Python installations are not required.
  MATLAB・Fiji・Pythonの別途インストールは不要です。

This Mac / このMac
  Double-click GLIA Center ATP Studio.app in the project folder.
  プロジェクトフォルダー内のGLIA Center ATP Studio.appをダブルクリックしてください。
  This Mac launcher uses the existing local runtime; it is not a standalone Mac distribution.
  このMac用ランチャーは既存の実行環境を使用します。Mac単独配布版ではありません。

Help / 操作ガイド
  docs/user-guide.html (Japanese + English)
  If startup fails, a message identifies the startup.log file.
  起動に失敗した場合は、startup.logの保存先をメッセージで表示します。

Experiment details are optional. Uncheck Include experiment to skip them.
実験情報は任意です。「実験情報を含める」のチェックを外すと省略できます。

Flow / 手順
  OIR metadata and calibration → MP4/PNG/TIFF/CSV → AQuA2 → ROA review → selected features
  OIR情報・時空間設定 → ファイル変換 → AQuA2 → ROA確認 → 採用結果の出力

Verification / 検証
  See docs/validation-status.html. Native Windows execution has not yet been verified.
  docs/validation-status.htmlを参照。Windows実機での動作確認は未実施です。

Original recordings, prior analyses and local QA projects are not included in the distribution.
実験原本・既存解析・ローカル検証プロジェクトは配布物に含めていません。

Preparation files / 準備時の出力
  Choosing an OIR sets Save to to the same folder. Check MP4, TIFF, CSV and PNG independently.
  OIR選択時に同じフォルダーを保存先に設定します。MP4・TIFF・CSV・PNGを個別に選択できます。
  Selected files are saved beside the OIR by default, with unique names.
  選択したファイルは初期設定でOIRと同じフォルダーに、重複しない名前で保存します。
  The project retains its working TIFF even when TIFF export is unchecked.
  TIFF出力を外しても、解析用TIFFはプロジェクト内に保持します。
