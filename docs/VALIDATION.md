# 検証状況 / Validation status

2026-10-28 · GLIA Center ATP Studio 0.3.0

| 項目 / Item | 状況 / Status |
|---|---|
| macOS arm64での機能検証 / Functional verification on macOS arm64 | 実OIRの情報読込・画素変換・AQuA2実行・MAT読込・ROA確認・結果出力を確認。 / Real OIR metadata, pixel conversion, AQuA2 execution, MAT import, review and export verified. |
| 自動検査 / Automated tests | 42件成功：従来の機能・Windows配布検査37件とProfessor表示の検査5件。 / 42 passing tests: the existing 37 functional/Windows packaging checks plus 5 Professor indicator checks. |
| Windowsパッケージ / Windows package | x64の実行環境・Java・依存ライブラリーを同梱。ハッシュ・ZIP整合性・GUIランチャー・ロゴを静的確認。 / x64 runtime, Java and dependencies bundled; hashes, ZIP integrity, GUI launcher and icon statically checked. |
| Windows実機 / Native Windows | **未検証 / Not yet executed or verified.** ローカルのZIP検証とは区別します。 / Separate from local ZIP validation. |
| Java版とMATLAB版の同等性 / Java–MATLAB equivalence | **未確立 / Not established.** 前処理・エンジン版を揃えたベンチマークが必要。 / Requires a harmonized benchmark with matching preprocessing and engine versions. |

実験原本、既存解析、ローカル検証プロジェクトおよび実データの画面画像は公開リポジトリに含めません。マニュアルの説明画面は実験結果ではありません。

Original recordings, prior analyses, local QA projects and screenshots of real data are excluded from the public repository. Illustrative manual screens are not experimental results.

## v0.2の確認 / v0.2 checks

- 原画像を変更せず、39イベントの既存記録の作業コピーで提案・同期表示・拡大範囲を確認しました。 / Suggestions, synchronized views and crop alignment were checked on a working copy of an existing 39-event recording without modifying originals.
- Shift選択、一括採否、Enter/A/R/H、メモ入力中の保護、Undo、フィルター後の次行選択、提案キャッシュと座標補正を自動検査しました。 / Automated checks cover Shift selection, batch review, Enter/A/R/H, note-entry protection, undo, filtered advancement, suggestion caching and coordinate offsets.
- 提案の分類精度・ATP特異性・偽陽性率は未検証です。 / Suggestion accuracy, ATP specificity and false-positive rates are not validated.

## v0.2.1の確認 / v0.2.1 checks

- 出力形式の未選択・各単独選択・混在・全選択を合成画素で検証。MP4フレーム数、TIFF画素と校正、CSV時刻と平均値、PNG読込を確認。 / Synthetic-pixel checks cover none, individual, mixed and all formats, verifying MP4 frame counts, TIFF pixels/calibration, CSV times/means and PNG readability.
- OIRフォルダーの自動設定、別保存先、再実行時の既存ファイル保持、ファイル衝突・中止時の後処理、外部出力なしでのプロジェクト再開を確認。 / Verified automatic OIR-folder selection, custom destinations, preservation on repeated runs, collision/cancellation cleanup and reopening without external derivatives.

## v0.2.2の確認 / v0.2.2 checks

制作者欄を英語3行に簡略化し、画面とAboutの表示を確認しました。機能検査33件はv0.2.1で実施済みです。 / Verified the simplified three-line English attribution in the sidebar and About. The 33 functional tests were last run for v0.2.1.

## v0.2.3の確認 / v0.2.3 checks

- Windowsの展開エラー`0x80010135`で報告された`qrc_qmake_Qt_labs_assetdownloader_init.cpp.obj`を旧配布物内で特定。未使用の`PySide6/qml/`を除外し、ZIPルートを`GLIA-ATP`に短縮しました。 / Located the exact object file reported in the Windows extraction error in the previous release. Excluded unused `PySide6/qml/` assets and shortened the archive root to `GLIA-ATP`.
- ZIP内の最長パスは211文字から130文字へ短縮。140 UTF-16単位を超えるパスをビルド時に拒否します。 / Longest archive path reduced from 211 to 130 characters; the build rejects paths over 140 UTF-16 code units.
- 全37件の自動検査がmacOS arm64で成功しました。検出パラメーター、エンジン、定量式は変更していません。 / All 37 automated checks passed on macOS arm64. Detection parameters, engine and measurement formulas are unchanged.
- 日本語・空白を含む一般的なWindows展開先を想定した全パスの長さ、ZIP整合性、ローカル展開後の全ファイルハッシュを確認しました。GitHubの認証にworkflow権限がないため、Windows自動実行は行っていません。 / Checked all path lengths against a representative Windows destination containing Japanese and spaces, ZIP integrity, and every file hash after local extraction. Native Windows automation was not run because the available GitHub authentication lacks workflow permission.

## v0.3.0の確認 / v0.3.0 checks

- Professorの元スプライトから作業中の6フレームをGIFへ変換し、透明背景、各フレームの時間、連続再生を確認しました。 / Converted the existing six active-work frames to GIF and checked transparency, frame timing and looping.
- バックグラウンド処理中のフレーム更新と経過時間、成功時の停止、中止処理中の継続、エラー表示前の停止、次の処理での再開を自動検査しました。 / Automated checks cover animation and elapsed-time updates during background work, stopping on success, continuing during cancellation, stopping before an error dialog and restarting for the next task.
- 1640×1040と1000×700の画面で表示位置を確認しました。氏名・メールは従来の3行を保持しています。 / Inspected placement at 1640×1040 and 1000×700. The existing three-line creator attribution is retained.
- macOS arm64で全42件の検査が成功しました。Windows配布の短いルート名とパス長検査も維持しています。 / All 42 checks passed on macOS arm64. The short Windows archive root and path-length checks remain in place.
