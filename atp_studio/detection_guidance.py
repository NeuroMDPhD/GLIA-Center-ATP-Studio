"""Explainable, local detection-setting guidance for the pinned AQuA2 engine.

Directions are grounded in the upstream helpers; step sizes are application
heuristics, not validated ATP thresholds or predictions of final event counts.
"""
from dataclasses import dataclass
import math
import re

RULE_VERSION = 'parameter-guide-1'
ENGINE_COMMIT = 'ca807872077a736e906698047bd718ce54754eda'
SOURCE_BASE = f'https://github.com/yu-lab-vt/AQuA2-Fiji/blob/{ENGINE_COMMIT}/src/main/java/va/vt/cbilAQuA2/'
SOURCES = {'activity': SOURCE_BASE + 'run/Step2Helper.java',
           'temporal': SOURCE_BASE + 'run/Step3Helper.java',
           'spatial': SOURCE_BASE + 'run/Step4Helper.java',
           'baseline': SOURCE_BASE + 'run/Step1Helper.java'}
LEGACY_DETECTION = dict(thrARScl=3.0, minSize=20, minDur=5, sigThr=3.5, smoXY=.5,
                         movAvgWin=25, cut=200, sourceSensitivity=8, sourceSzRatio=.01,
                         maxDelay=.6, regMaskGap=5, memory_gb=12, median_radius=1)
DEFAULT_DETECTION = {**LEGACY_DETECTION, 'thrARScl': 3.5, 'minSize': 30, 'minDur': 6, 'sigThr': 4.0}


@dataclass(frozen=True)
class Parameter:
    key: str
    title: str
    low: float
    high: float
    step: float
    decimals: int
    unit: str
    higher: str
    lower: str
    caution: str


PARAMETERS = [
    Parameter('thrARScl', 'Activity threshold / 活動閾値', .1, 20, .1, 2, 'noise SD',
              'Rejects weaker activity; usually fewer weak candidates. / 弱い活動を除き、弱い候補が減る傾向。',
              'Includes weaker activity and more noise; regions may connect. / 弱い活動とノイズを含み、領域がつながる場合があります。',
              'Final ROA count need not change monotonically because segmentation also changes. / 分割も変わるため、最終ROA数が一定方向に変化するとは限りません。'),
    Parameter('minSize', 'Minimum area / 最小面積', 1, 100000, 1, 0, 'pixels',
              'Rejects small regions and small sources. / 小さな領域・発生源を除きます。',
              'Retains smaller regions, including small noise patches. / 小さな領域と小さいノイズを残しやすくします。',
              'This is area in pixels, not a radius or cell size. / 画素の面積であり、半径や細胞サイズではありません。'),
    Parameter('minDur', 'Minimum duration / 最小持続', 1, 10000, 1, 0, 'frames',
              'Rejects shorter candidates. / 短い候補を除きます。',
              'Retains briefer transients and brief noise. / 短い活動や瞬間的なノイズを残しやすくします。',
              'Candidate time span is tested; this is not a required continuous bright-pixel count. / 候補の時間幅を判定します。連続した高輝度フレーム数の条件ではありません。'),
    Parameter('sigThr', 'Seed significance / シード有意性', .1, 20, .1, 2, 'score',
              'Requires stronger temporal seed evidence. / 時間分割シードに強い証拠を要求します。',
              'Allows weaker temporal seeds; false seeds may increase. / 弱い時間分割シードを許容し、偽シードが増える場合があります。',
              'Can alter splitting and event retention, not just total count. / 分割と候補の採否の両方に影響します。'),
    Parameter('sourceSensitivity', 'Spatial source sensitivity / 空間分離感度', 1, 10, 1, 0, 'level',
              'Separates sources at smaller onset-delay differences; may split more. / 小さい開始遅延の差でも発生源を分けやすくします。',
              'Requires larger delay differences; sources may stay together. / 大きな遅延差を要求し、発生源をまとめやすくします。',
              'Acts within an event region; cannot distinguish all simultaneous neighboring signals. / 領域内の分離です。同時発生の隣接信号を必ず分離できるわけではありません。'),
    Parameter('maxDelay', 'Temporal merge tolerance / 時間統合の許容度', 0, 1, .05, 2, 'ratio',
              'Allows more dissimilar timing to merge into one super-event. / 時間特性が異なる領域も統合しやすくします。',
              'Makes temporal merging stricter; may separate more regions. / 時間統合を厳しくし、領域を分けやすくします。',
              'This is a normalized dissimilarity threshold, not a delay in seconds. / 正規化した非類似度の閾値であり、秒単位の遅延ではありません。'),
    Parameter('sourceSzRatio', 'Minimum source fraction / 最小発生源比率', 0, 1, .005, 3, 'fraction',
              'Rejects small source seeds within a super-event; may split less. / 大領域内の小さな発生源を除き、分離を抑える場合があります。',
              'Allows smaller source seeds; may split more. / 小さな発生源を許容し、分離を増やす場合があります。',
              'Minimum area also applies; 0.01 means 1% of the parent region. / 最小面積の条件も適用されます。0.01は元領域の1%です。'),
    Parameter('smoXY', 'Gaussian smoothing / ガウス平滑化', 0, 5, .1, 2, 'sigma pixels',
              'Smooths spatial noise more, but can blur neighboring signals. / 空間ノイズを抑えますが、隣接信号をぼかす場合があります。',
              'Preserves spatial detail and more noise. / 空間的な細部とノイズを残します。',
              '0 disables this AQuA2 filter; distinct from median preprocessing. / 0でAQuA2のこのフィルターを無効化。メディアン前処理とは別です。'),
    Parameter('movAvgWin', 'Baseline smoothing / 基準線平滑化', 2, 1000, 1, 0, 'frames',
              'Uses a smoother baseline estimate with less rapid variation. / 基準線を滑らかにし、速い変動を抑えます。',
              'Lets the baseline estimate follow faster fluctuations. / 基準線を速い変動に追従しやすくします。',
              'Event count has no fixed direction. Engine bias-table support ends at 1000 frames. / イベント数の方向は一定しません。補正表の上限は1000フレームです。'),
    Parameter('cut', 'Baseline segment / 基準線区間', 10, 9999, 10, 0, 'frames',
              'Finds baseline minima over a longer interval; adapts less locally. / 長い区間で基準線の最小値を探し、局所変動への追従を抑えます。',
              'Follows local drift more, but may absorb sustained signals. / 局所的なドリフトに追従しますが、持続信号を基準線に含む場合があります。',
              'AQuA2 clips this to recording length. 9999 avoids the pinned bias-table boundary. / 記録長で切り詰めます。固定版の補正表境界を避ける上限は9999です。'),
    Parameter('regMaskGap', 'Edge crop / 周辺除外', 0, 100, 1, 0, 'pixels per edge',
              'Excludes a wider border and any real events there. / 広い周辺を除外し、そこにある実信号も除きます。',
              'Includes more of the image edge and its artifacts. / 周辺の画素とアーティファクトを含めます。',
              'Cropping does not correct motion. / 切り出しは動き補正ではありません。'),
    Parameter('median_radius', 'Median radius / メディアン半径', 0, 5, 1, 0, 'pixels',
              'Suppresses isolated pixels more, but may erase tiny real events. / 孤立画素を抑えますが、小さい実信号も消す場合があります。',
              'Preserves smaller features and more pixel noise. / 小さな構造と画素ノイズを残します。',
              'Radius 1 uses 3×3 pixels; 0 disables preprocessing. / 半径1は3×3画素。0で前処理を無効化します。'),
    Parameter('memory_gb', 'Memory limit / メモリ上限', 2, 64, 1, 0, 'GB',
              'Allows a larger Java heap if enough RAM is available. / 空きRAMがあればJavaのヒープを大きくできます。',
              'Leaves more RAM for the system but can cause Java memory errors. / システムにRAMを残しますが、Javaのメモリ不足が起こり得ます。',
              'Does not tune event counts or cap total app RAM. Use less than available RAM. / イベント数の調整値でもアプリ全体の上限でもありません。空きRAMより低く設定します。'),
]
PARAMETER_BY_KEY = {p.key: p for p in PARAMETERS}


def bounds(key, context=None, settings=None):
    p = PARAMETER_BY_KEY[key]
    low, high = p.low, p.high
    shape = (context or {}).get('shape')
    if shape:
        n, h, w = map(int, shape)
        if key in ('movAvgWin', 'minDur'):
            high = min(high, n)
        if key == 'regMaskGap':
            high = min(high, (min(h, w) - 5) // 2)
        if key == 'minSize':
            gap = int((settings or DEFAULT_DETECTION).get('regMaskGap', 5))
            high = min(high, max(0, h - 2 * gap) * max(0, w - 2 * gap))
    return low, high


def format_value(value):
    return f'{value:g}'


def validate_settings(settings, context=None):
    cfg = {**DEFAULT_DETECTION, **settings}
    for p in PARAMETERS:
        value = cfg[p.key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{p.title}: enter a finite number. / 有限の数値を入力してください。')
        if p.decimals == 0 and int(value) != value:
            raise ValueError(f'{p.title}: use an integer. / 整数を入力してください。')
        low, high = bounds(p.key, context, cfg)
        if not low <= value <= high:
            raise ValueError(f'{p.title}: allowed {low:g}–{high:g}. / 許容範囲 {low:g}–{high:g}。')
        cfg[p.key] = int(value) if p.decimals == 0 else float(value)
    return cfg


def range_text(key, context=None, settings=None):
    p = PARAMETER_BY_KEY[key]
    low, high = bounds(key, context, settings)
    return f'{low:g}–{high:g} {p.unit}'


def calibrated_value(key, value, context=None):
    context = context or {}
    dt, px, py = (context.get(k) for k in ('interval_s', 'pixel_x_um', 'pixel_y_um'))
    if key in ('minDur', 'movAvgWin', 'cut') and dt:
        effective = min(value, context['shape'][0]) if key == 'cut' and context.get('shape') else value
        text = f'{effective * dt:g} s (N×Δt)'
        return f'Effective / 実効: {effective:g} frames\n{text}' if effective != value else text
    if key == 'minSize' and px and py:
        return f'{value * px * py:g} µm²'
    if key == 'sourceSzRatio':
        return f'{100 * value:g}% of parent region / 元領域の比率'
    if key == 'median_radius':
        return f'{2 * int(value) + 1} × {2 * int(value) + 1} pixels'
    if key == 'smoXY' and px:
        return f'σ ≈ {value * px:g} µm'
    return ''


@dataclass(frozen=True)
class Issue:
    key: str
    title: str
    parameter: str | None
    operation: str
    amount: float
    advice: str
    aliases: tuple[str, ...]


ISSUES = [
    Issue('noise', 'Too many weak/noisy events / 弱い・ノイズ候補が多い', 'thrARScl', 'add', .5,
          'Raise the activity threshold slightly, then inspect weak true signals you might lose. / 活動閾値を少し上げ、弱い実信号を失っていないか確認します。',
          ('too many', 'noise', 'false positive', 'ノイズ', '多すぎ', '多い', '偽陽性')),
    Issue('weak', 'Weak signals are missed / 弱い信号を見逃す', 'thrARScl', 'add', -.5,
          'Lower the activity threshold slightly; also verify channel, calibration and traces. Noise may increase. / 活動閾値を少し下げます。チャネル・校正・波形も確認してください。ノイズが増える場合があります。',
          ('too few', 'no events', 'weak signal', 'missed', '見逃', '少な', '検出されない', '検出されません')),
    Issue('small_noise', 'Too many tiny regions / 小さい領域が多い', 'minSize', 'scale', 1.25,
          'Raise minimum area by about 25%. Check that small real ROAs remain. / 最小面積を約25%増やし、小さな実ROAが残るか確認します。',
          ('tiny regions', 'small noise', 'speckles', '小さい領域', '微小ノイズ', '点状')),
    Issue('brief_noise', 'Brief flashes dominate / 短い点滅が多い', 'minDur', 'add', 1,
          'Require one more frame of candidate duration. Real brief transients may disappear. / 最小持続を1フレーム増やします。短い実信号も除かれる場合があります。',
          ('brief flashes', 'spikes', 'flicker', '点滅', '瞬間的', 'スパイク')),
    Issue('short_missed', 'Short real signals are missed / 短い実信号を見逃す', 'minDur', 'add', -1,
          'Lower minimum duration by one frame and inspect the added brief candidates. / 最小持続を1フレーム減らし、追加された短い候補を確認します。',
          ('short signals', 'brief signals', '短い信号', '短い実信号')),
    Issue('spatial_merged', 'Neighboring sources merge / 隣接信号が一つになる', 'sourceSensitivity', 'add', 1,
          'Increase spatial source sensitivity one level. Compare separate onset locations in the movie; one spreading event may be over-split. / 空間分離感度を1段階上げます。動画で開始位置を比較してください。一つの伝播活動を分けすぎる場合があります。',
          ('merged', 'merge', 'joined', 'neighbor', '合体', '一つ', '結合', '隣接', '統合')),
    Issue('spatial_split', 'One spatial event is fragmented / 一つの活動が細かく分かれる', 'sourceSensitivity', 'add', -1,
          'Lower spatial source sensitivity one level. Distinct nearby sources may remain merged. / 空間分離感度を1段階下げます。近接する別の発生源も統合される場合があります。',
          ('fragmented', 'over split', 'over-split', 'too many pieces', 'split', '分かれ', '分割', '細切れ')),
    Issue('temporal_merged', 'Separate time courses merge / 時間特性の異なる活動が統合される', 'maxDelay', 'add', -.1,
          'Reduce temporal merge tolerance slightly. Compare time courses and avoid splitting a single propagation pattern. / 時間統合の許容度を少し下げます。波形を比較し、一つの伝播を分けすぎないか確認します。',
          ('temporal merge', 'peaks merge', 'time courses merge', '時間特性', '時間的に統合', 'ピークが一つ')),
    Issue('temporal_split', 'Similar time courses stay split / 似た時間波形が分離したまま', 'maxDelay', 'add', .1,
          'Increase temporal merge tolerance slightly. Distinct events may also merge. / 時間統合の許容度を少し上げます。別イベントも統合される場合があります。',
          ('temporal split', 'similar traces', 'similar time', '似た波形', '似た時間', '時間的に分割')),
    Issue('edge', 'Artifacts near the image border / 画像周辺のアーティファクト', 'regMaskGap', 'add', 1,
          'Exclude one more border pixel. Real edge events are removed too; inspect the crop. / 各辺をさらに1画素除外します。周辺の実信号も失うため、範囲を確認します。',
          ('border', 'edge', '周辺', '画像端', '端の')),
    Issue('drift', 'Baseline drift or bleaching / 基準線ドリフト・退色', None, 'none', 0,
          'Inspect raw traces and acquisition stability first. Baseline windows change sustained signals and have no universal correction. The app does not perform explicit bleaching or motion correction. / 原波形と撮影の安定性を先に確認してください。基準線窓は持続信号にも影響し、一律の補正値はありません。このアプリは明示的な退色・動き補正を行いません。',
          ('drift', 'bleach', 'baseline', 'ドリフト', '退色', '基準線')),
    Issue('motion', 'Motion or global flashes / 動き・全視野の点滅', None, 'none', 0,
          'Inspect the original movie and motion first. Threshold changes cannot establish whether a global flash is biological; use a separate verified motion-correction workflow when needed. / 原動画と動きを確認してください。閾値変更だけで全視野点滅の由来は判定できません。必要なら別途検証した動き補正を使います。',
          ('motion', 'movement', 'global flash', '動き', 'ずれ', '全視野')),
    Issue('memory', 'Slow or out of memory / 遅い・メモリ不足', None, 'none', 0,
          'Check available RAM and the log. Leave memory for Python and the OS; raising the Java limit beyond available RAM can worsen failure. Event thresholds should follow signal quality. / 空きRAMとログを確認してください。PythonとOS用のメモリを残し、空きRAMを超えるJava設定を避けます。検出閾値は信号の質に基づいて調整します。',
          ('slow', 'memory', 'ram', '遅い', 'メモリ')),
]
ISSUE_BY_KEY = {p.key: p for p in ISSUES}


def match_issues(text):
    """Local keyword search only. Ambiguous descriptions require a user choice."""
    text = re.sub(r'\s+', ' ', text.casefold()).strip()
    if not text:
        return []
    return [issue.key for issue in ISSUES if any(term in text for term in issue.aliases)]


def recommend(issue_key, settings, context=None):
    cfg = validate_settings(settings, context)
    issue = ISSUE_BY_KEY[issue_key]
    result = {'rule_version': RULE_VERSION, 'issue': issue_key, 'before': cfg,
              'after': dict(cfg), 'advice': issue.advice, 'changes': []}
    if issue.parameter is None:
        return result
    p = PARAMETER_BY_KEY[issue.parameter]
    before = cfg[p.key]
    value = before + issue.amount if issue.operation == 'add' else before * issue.amount
    if p.decimals == 0:
        value = math.ceil(value) if value > before else math.floor(value)
    else:
        value = round(value, p.decimals)
    low, high = bounds(p.key, context, cfg)
    value = min(high, max(low, value))
    value = int(value) if p.decimals == 0 else float(value)
    if value == before:
        result['advice'] += '\nAlready at the allowed limit; no further change proposed. / 許容範囲の端のため、追加変更を提案しません。'
        return result
    result['after'][p.key] = value
    validate_settings(result['after'], context)
    result['changes'].append({'key': p.key, 'before': before, 'after': value,
                              'effect': p.higher if value > before else p.lower, 'caution': p.caution})
    return result
