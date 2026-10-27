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
