# 検証状況 / Validation status

2026-10-27 · ATP ROA Studio 0.1.0

| 項目 / Item | 状況 / Status |
|---|---|
| macOS arm64での機能検証 / Functional verification on macOS arm64 | 実OIRの情報読込・画素変換・AQuA2実行・MAT読込・ROA確認・結果出力を確認。 / Real OIR metadata, pixel conversion, AQuA2 execution, MAT import, review and export verified. |
| 自動検査 / Automated tests | 15件成功：校正、単位、打切り、既知の減衰、座標、入力照合、採否保存、空出力、実験情報の省略など。 / 15 passing tests covering calibration, units, censoring, known decay, coordinates, input matching, review persistence, empty selection and experiment opt-out. |
| Windowsパッケージ / Windows package | x64の実行環境・Java・依存ライブラリーを同梱。ハッシュ・ZIP整合性・GUIランチャー・ロゴを静的確認。 / x64 runtime, Java and dependencies bundled; hashes, ZIP integrity, GUI launcher and icon statically checked. |
| Windows実機 / Native Windows | **未検証 / Not yet executed or verified.** |
| Java版とMATLAB版の同等性 / Java–MATLAB equivalence | **未確立 / Not established.** 前処理・エンジン版を揃えたベンチマークが必要。 / Requires a harmonized benchmark with matching preprocessing and engine versions. |

実験原本、既存解析、ローカル検証プロジェクトおよび実データの画面画像は公開リポジトリに含めません。マニュアルの説明画面は実験結果ではありません。

Original recordings, prior analyses, local QA projects and screenshots of real data are excluded from the public repository. Illustrative manual screens are not experimental results.
