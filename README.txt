GLIA Center ATP Studio 0.4.0 — Research preview / 研究用プレビュー

Windows portable package / Windowsポータブル版
  dist/GLIA-Center-ATP-Studio-Windows-x64.zip
  Extract All to a short destination such as C:\GLIA, open GLIA-ATP, then double-click GLIA Center ATP Studio.exe.
  「すべて展開」でC:\GLIAなどの短い保存先を指定し、GLIA-ATP内のGLIA Center ATP Studio.exeをダブルクリックしてください。
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

Processing indicator / 処理中の表示
  Professor animates at the bottom left while a task runs, with status and elapsed time.
  処理中は左下でProfessorが動き、状態と経過時間を表示します。
  After Cancel, Stopping remains visible until the task ends. The animation then stops.
  Cancel後は処理終了まで「中止処理中」を表示し、終了時にアニメーションが停止します。
  v0.4.0 includes the shorter Windows extraction paths introduced in v0.2.3.
  v0.4.0はv0.2.3のWindows展開パス短縮も含みます。

Experiment details are optional. Uncheck Include experiment to skip them.
実験情報は任意です。「実験情報を含める」のチェックを外すと省略できます。

Flow / 手順
  OIR metadata and calibration → MP4/PNG/TIFF/CSV → AQuA2 → ROA review → selected features
  OIR情報・時空間設定 → ファイル変換 → AQuA2 → ROA確認 → 採用結果の出力

Verification / 検証
  See docs/validation-status.html. Native Windows startup and end-to-end execution remain unverified.
  docs/validation-status.htmlを参照。Windows実機での起動・全工程検証は未実施です。

Extraction error 0x80010135 / 展開エラー
  Use v0.2.3 or later, and extract fully into a new short destination such as C:\GLIA.
  v0.2.3以降を新しい短い保存先（例：C:\GLIA）に全て展開してください。
  Do not skip files or merge with a partly extracted older version. Existing analysis projects can be opened separately.
  ファイルをスキップせず、途中まで展開した旧版と混在させないでください。既存の解析プロジェクトは別途開けます。

Original recordings, prior analyses and local QA projects are not included in the distribution.
実験原本・既存解析・ローカル検証プロジェクトは配布物に含めていません。

Preparation files / 準備時の出力
  Choosing an OIR sets Save to to the same folder. Check MP4, TIFF, CSV and PNG independently.
  OIR選択時に同じフォルダーを保存先に設定します。MP4・TIFF・CSV・PNGを個別に選択できます。
  Selected files are saved beside the OIR by default, with unique names.
  選択したファイルは初期設定でOIRと同じフォルダーに、重複しない名前で保存します。
  The project retains its working TIFF even when TIFF export is unchecked.
  TIFF出力を外しても、解析用TIFFはプロジェクト内に保持します。

Detect adjustment helper / 検出の調整ガイド
  Stricter defaults: activity threshold 3.5, area 30 pixels, duration 6 frames, seed significance 4.0.
  厳しめの初期値：活動閾値3.5、最小面積30画素、最小持続6フレーム、シード有意性4.0。
  Select a problem or search in English/Japanese. Preview the change, apply it, then Run AQuA2.
  問題を選ぶか英語・日本語で検索し、変更を確認・適用してから再検出してください。
  Parameters & ranges explains increasing/decreasing each value; Undo restores the last adjustment.
  「値と範囲」で増減の影響を確認でき、Undoで直前の調整を戻せます。
  Earlier defaults and Use last run are available. Existing results and reviews are preserved.
  以前の初期値・前回の設定も選べます。既存の結果と確認履歴は保持します。
