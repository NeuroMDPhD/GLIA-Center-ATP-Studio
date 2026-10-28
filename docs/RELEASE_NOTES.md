# v0.4.0 — 検出調整ガイドと厳しめの初期値 / Guided detection and stricter defaults

- 活動閾値3.0→3.5、最小面積20→30画素、最小持続5→6フレーム、シード有意性3.5→4.0。 / Activity threshold 3.0→3.5, minimum area 20→30 pixels, minimum duration 5→6 frames and seed significance 3.5→4.0.
- 問題の選択・英語/日本語キーワード入力から、一つの値の小幅な調整を提案します。適用前に値と影響を確認し、Undoで戻せます。 / Select a problem or search with English/Japanese keywords to preview a small adjustment to one parameter, apply it and undo it.
- 13項目の範囲、増減の影響、秒・µm²換算を表示します。以前の初期値・前回の設定も選択できます。 / Displays ranges and effects for 13 parameters, with seconds/µm² conversions and options to restore earlier defaults or last-run settings.
- 推奨の変更履歴を保存し、既存の結果・確認履歴を保持します。基準線窓の範囲を固定版エンジンの補正表に合わせて制限しました。 / Saves applied-guidance provenance and preserves existing results/reviews. Baseline-window limits follow the pinned engine's bias-table support.
- GUIを解放する順序を修正し、検証時のPython終了クラッシュに対応しました。 / Corrects GUI disposal order to address the Python shutdown crash seen during validation.
- Professorの処理中アニメーションと、短いWindows展開パスを含みます。日本語・英語マニュアルを更新しました。 / Includes the Professor activity animation and shorter Windows extraction paths, with an updated Japanese–English manual.

提案は設定調整の開始点です。実信号の採否は確認が必要で、最終ROA数の減少を保証するものではありません。 / Suggestions are starting points for tuning. Review real signals; fewer final ROAs are not guaranteed.

検証 / Validation: 73 automated tests passed on macOS arm64, including independent process exit checks. Native macOS startup/shutdown and small-screen layout checked. Native Windows execution and real-data accuracy of the new presets remain unverified.

**起動 / Start:** 新しい短い保存先（例：`C:\GLIA`）にZIP全体を展開し、`GLIA-ATP`内の`GLIA Center ATP Studio.exe`をダブルクリックします。既存プロジェクトは`Open project`で開けます。 / Extract the entire ZIP into a fresh short destination such as `C:\GLIA`, then double-click `GLIA Center ATP Studio.exe` inside `GLIA-ATP`. Reopen existing projects with `Open project`.

# v0.3.0 — Professorによる処理中表示 / Professor activity indicator

- 処理中は左下でProfessorのGIFが動き、`Working / 処理中`と経過時間を表示します。 / Professor animates at the bottom left while a task runs, with status and elapsed time.
- メタデータ読込、ファイル変換、AQuA2、提案計算および出力で同じ表示を使用します。 / The indicator covers metadata reading, file conversion, AQuA2, suggestion calculation and export.
- 中止要求後は実際の終了まで`Stopping… / 中止処理中…`を表示し、完了・中止・エラー時に停止します。 / After Cancel, `Stopping… / 中止処理中…` remains visible until the task ends; the animation stops on completion, cancellation or error.
- ユーザーが選択したProfessorの既存アニメーションを使用します。 / Uses the existing animation from the user's selected Professor pet.
- v0.2.3のWindows展開修正、従来の確認・選択・出力機能を含みます。 / Includes the v0.2.3 Windows extraction fix and previous review, selection and export features.
- 日本語・英語マニュアルに動作例を追加しました。 / Adds an animation preview and screenshot to the Japanese–English manual.

検証 / Validation: 42 automated tests passed on macOS arm64. Verified animation playback during a worker task, elapsed time, success, cancellation, errors, restart and the 1000×700 layout. ZIP paths remain limited to 140 UTF-16 units. Native Windows execution remains unverified.

**起動 / Start:** ZIPを新しい短い保存先（例：`C:\GLIA`）に全て展開し、`GLIA-ATP`内の`GLIA Center ATP Studio.exe`をダブルクリックします。 / Extract the entire ZIP into a new short destination such as `C:\GLIA`, then double-click `GLIA Center ATP Studio.exe` inside `GLIA-ATP`.

# v0.2.3 — Windows展開エラーの修正 / Windows extraction fix

WindowsでZIPを展開する際の`0x80010135`（パスが長すぎる）に対応しました。 / Addresses `0x80010135` (path too long) while extracting the Windows ZIP.

- 未使用のQt QMLファイルを配布から除外し、内部フォルダー名を`GLIA-ATP`に短縮しました。最長パスは211文字から130文字です。 / Removes unused Qt QML files and shortens the internal folder name to `GLIA-ATP`, reducing the longest archive path from 211 to 130 characters.
- Qt Widgets、Windowsプラグイン、Python、Java、解析ライブラリーおよびライセンスを保持します。 / Retains Qt Widgets, Windows plugins, Python, Java, analysis libraries and licenses.
- 配布時のパス長検査を追加しました。 / Adds path-length regression checks during packaging.
- 検出パラメーター・測定値の計算・保存済みプロジェクト形式は変更していません。 / Detection parameters, measurement calculations and saved project formats are unchanged.

**起動 / Start:** ZIPを新しい短い保存先（例：`C:\GLIA`）に全て展開し、`GLIA-ATP`内の`GLIA Center ATP Studio.exe`をダブルクリックしてください。旧版の途中まで展開したフォルダーに重ねず、ファイルをスキップしないでください。 / Extract the complete ZIP into a new short destination such as `C:\GLIA`, then double-click `GLIA Center ATP Studio.exe` inside `GLIA-ATP`. Do not merge it into a partially extracted older copy or skip files.

既存の解析プロジェクトは保持し、新版の`Open project`から再開できます。 / Preserve existing analysis projects and resume them with `Open project` in the new version.

検証 / Validation: 37 automated tests passed on macOS arm64. ZIP integrity, extracted file hashes and path lengths checked locally. Native Windows startup and end-to-end execution remain unverified.

# v0.2.2 — 制作者表示 / Creator attribution

左下とAboutの制作者欄を次の英語3行に統一しました。 / The sidebar and About use the same three-line English attribution:

Creator<br>
Seunghwan Choi<br>
medic@khu.ac.kr

画面表示を確認しました。解析機能はv0.2.1と同じです。Windows実機での実行は未検証です。 / Display verified; analysis behavior is unchanged from v0.2.1. Native Windows execution remains unverified.

---

# v0.2.1 — 出力形式の選択 / Choose preparation outputs

OIR選択時に同じフォルダーを初期保存先とし、MP4・TIFF・CSV・PNGをそれぞれ選択できるようになりました。

Choosing an OIR now defaults to its folder, with independent MP4, TIFF, CSV and PNG checkboxes.

- 選択した出力だけを保存先に作成。別フォルダーも指定可能。 / Save only selected formats beside the OIR, or choose another destination.
- 原本・既存出力を保持し、再実行ごとに別名を使用。 / Preserve originals and existing outputs with unique filenames for each preparation.
- 全形式を外しても解析・再開が可能。内部の解析用TIFFは保持。 / Analysis and reopening work with all external formats unchecked; the internal working TIFF remains.
- 日本語・英語マニュアルと画面例を更新。 / Updated Japanese–English manual and screenshots.

検証 / Validation: 33 automated tests passed on macOS arm64. Native Windows execution remains unverified.

ZIP全体を展開して `GLIA Center ATP Studio.exe` をダブルクリックします。MATLAB不要です。 / Extract the entire Windows ZIP and double-click the executable; MATLAB is not required.

---

# v0.2.0 — GLIA Center ATP Studio

全視野・ROA拡大像・波形を比較しながら、根拠付きの提案とキーボードで効率的に確認できるようになりました。

Review ROAs with synchronized full-field and close-up views, explainable suggestions and keyboard batch decisions.

- 全視野＋拡大像、波形下の再生バー。 / Full-field and close-up views; playback below the trace.
- 信号候補・要確認・ノイズ疑いと根拠、調整可能な基準、出力への保存。 / Signal-candidate, check and noise-like suggestions with reasons, adjustable thresholds and export snapshots.
- Shift複数選択、A/Enter採用、R/Delete除外、H保留、Uリセット、Ctrl/Cmd+Zで直前の操作を戻す。 / Shift selection, A/Enter Keep, R/Delete Exclude, H Hold, U Reset and Ctrl/Cmd+Z Undo.
- GLIA Center ATP Studioへ改名。大学サイトを参考に青・紺へ変更し、IBM Plex Sans / JPを同梱。制作者・連絡先を左下に表示。 / Renamed to GLIA Center ATP Studio, with university-inspired blue/navy colors, bundled IBM Plex Sans / JP, and creator/contact at bottom left.

`GLIA-Center-ATP-Studio-Windows-x64.zip`を全て展開し、`GLIA Center ATP Studio.exe`をダブルクリックします。 / Extract the full Windows ZIP and double-click `GLIA Center ATP Studio.exe`.

`GLIA-Center-ATP-Studio-Manual-JA-EN.zip`内の`manual.html`が日本語・英語マニュアルです。 / Open `manual.html` in the manual ZIP for Japanese–English instructions.

既存のプロジェクトを開けます。提案は人による確認の補助で、検証済みATP分類器ではありません。Windows実機での実行検証は未実施です。 / Existing projects remain compatible. Suggestions assist human review and are not a validated ATP classifier. Native Windows execution has not yet been verified.

---

# v0.1.0 — 研究用プレビュー / Research preview

OIR選択から、時空間設定、AQuA2検出、ROA確認、採用結果の出力までをまとめた日本語・英語対応アプリです。

A Japanese–English desktop workflow from OIR selection and calibration through AQuA2 detection, ROA review and selected-result export.

- `ATP-ROA-Studio-Windows-x64.zip`：全体を展開し、`ATP ROA Studio.exe`をダブルクリックします。MATLAB不要です。 / Extract the entire archive and double-click `ATP ROA Studio.exe`; no MATLAB installation required.
- `ATP-ROA-Studio-Manual-JA-EN.zip`：日本語・英語マニュアルです。展開して`manual.html`を開きます。 / Extract and open `manual.html` for the Japanese–English manual.
- `.sha256`：ダウンロードしたZIPの整合性を確認するハッシュです。 / Checksums for verifying the downloaded archives.

**Windows 10/11 x64向け。Windows実機実行は未検証です。Java版と既存MATLAB解析の数値的同等性も未確立です。**

**Targets Windows 10/11 x64. Native Windows execution is not yet verified. Numerical equivalence to existing MATLAB analyses is not established.**

原本は上書きしません。実験データは配布物に含めません。 / Source recordings are not overwritten; experimental data is not included in the distribution.
