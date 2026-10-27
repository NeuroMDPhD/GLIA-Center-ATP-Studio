# 検証状況 / Validation status

2026-10-27 · GLIA Center ATP Studio 0.2.2

| 項目 / Item | 状況 / Status |
|---|---|
| macOS arm64での機能検証 / Functional verification on macOS arm64 | 実OIRの情報読込・画素変換・AQuA2実行・MAT読込・ROA確認・結果出力を確認。 / Real OIR metadata, pixel conversion, AQuA2 execution, MAT import, review and export verified. |
| 自動検査 / Automated tests | 33件成功：校正、単位、打切り、既知の減衰、座標、入力照合、採否保存、空出力、実験情報の省略など。 / 33 passing tests covering calibration, units, censoring, known decay, coordinates, input matching, review persistence, empty selection and experiment opt-out. |
| Windowsパッケージ / Windows package | x64の実行環境・Java・依存ライブラリーを同梱。ハッシュ・ZIP整合性・GUIランチャー・ロゴを静的確認。 / x64 runtime, Java and dependencies bundled; hashes, ZIP integrity, GUI launcher and icon statically checked. |
| Windows実機 / Native Windows | **未検証 / Not yet executed or verified.** |
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
