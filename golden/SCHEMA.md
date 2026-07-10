# ゴールデンテストベクター（damage golden vectors）

ダメージ計算の 3 実装（Swift = PokeLabo iOS / Kotlin = PokeLabo-Android / Python = pokelabo-ai）の
ドリフトを機械検知するための共有テストベクター。

- **正本はこのディレクトリ**（`golden/damage/*.json`）。ただし**手編集は禁止**
- ケースの定義・期待値は iOS リポジトリの `tools/golden-gen`（参照実装 = `PokeLabo/Domain`）から生成する
- **アプリ配信用の `manifest.json` には含めない**（アプリのリモート同期とは無関係）
- **`update.py` はこのディレクトリに触れない**こと（update.py 改修時の注意）

## 運用フロー（新メカニクス追加・仕様変更時）

```
1. iOS (PokeLabo) でメカニクスを実装しユニットテストを通す
2. tools/golden-gen/Sources/GoldenKit/Cases/ にケースを追加
   （新分岐は発動 + 非発動の最低 2 ケース。特性は ability:<nameEn> タグ必須 —
     resolver との突合せテストが漏れを検出する）
3. PokeLabo リポジトリで scripts/generate_golden.sh を実行 → ここに diff が出る
4. pokelabo-data をコミット & push
5. PokeLabo-Android / pokelabo-ai で pull → ベクターテストが fail → 移植 → green
```

再生成の決定性確認: `PokeLabo/scripts/verify_golden.sh`（2 回生成してケースファイルのバイト一致を検証）

## ファイル構成

```
golden/damage/
├ index.json   {schemaVersion, generator:{sourceCommit, generatedAt}, files:[{name, caseCount}]}
├ basics.json / rounding.json / stats.json / context.json / weather_terrain.json
├ abilities_attacker.json / abilities_defender.json / items.json
├ special_moves.json / mega.json / regressions.json
```

- 各ファイルはケースの JSON 配列（id 昇順・キーはソート済み・整形出力）
- **ケースファイルは決定的**（同一ソースから何度生成しても diff ゼロ）。生成日時・コミット SHA は index.json のみ

## スキーマ（schemaVersion 1）

```jsonc
{
  "id": "ability_atk_tough_claws_on",       // 全体で一意（英小文字スネークケース）
  "description": "かたいツメ: 接触技1.3倍",  // 日本語・ゲーム用語のみ
  "tags": ["ability", "ability:Tough Claws"],
  "input": { "level": 50, "attacker": {...}, "defender": {...}, "move": {...}, "context": {...} },
  "expected": {
    "isImmune": false,
    "minDamage": 103, "maxDamage": 123,
    "allDamages": [103, ...],               // 昇順ソート済み
    "typeEffectiveness": 1.0                // 参考情報（比較必須は上 4 項目）
  }
}
```

### 比較規約

- 比較必須: `isImmune` / `minDamage` / `maxDamage` / `allDamages`（**昇順ソートして比較**）
- `allDamages` は通常 16 要素。**おやこあい等の合成分布は 16 の冪**（参照実装は 2 発合成で 256 要素）
- `isImmune: true` のとき `allDamages` は全 0
- `typeEffectiveness` は実装が公開していなければ比較省略可

### 入力（自己完結・データファイル非依存）

トークンは既存アプリ JSON（pokemon.json / moves.json）と同一表現。
**デフォルト値と等しいフィールドは省略される**。省略時の既定値:

| フィールド | 既定値 | 備考 |
|---|---|---|
| `input.level` | 50 | Champions 固定 |
| combatant `.types` | 常に出力 | 英小文字（"fire" 等） |
| combatant `.ability` | "None" | **nameEn**（EffectResolver のマッチキー） |
| combatant `.item` | null | nameEn |
| combatant `.nature` | "serious" | 英名小文字 |
| combatant `.evs` / `.ranks` | 全 0 | 非 0 のみのスパース辞書 `{"attack": 32}`。EV は 0..32（**直接加算**、本家の /4 ではない）。IV は全実装 31 固定 |
| combatant `.status` | null | "burn" / "paralysis" / "poison" / "badPoison" / "sleep" / "freeze" |
| combatant `.weight` | 50.0 | kg（重さ依存技用） |
| move `.id` | 0 | 特殊挙動判定に id を使う技（473 サイコショック等）のみ実 id |
| move `.power` | 出力（null = 威力なし） | 固定ダメージ技等 |
| move `.flags` | 全 false | true のみのスパース辞書。キーは MoveFlags と同名 |
| move `.powerType` | "fixed" | "fixedDamage" / {"variable": "grassKnot"}（moves.json と同形式） |
| move `.hits` | "single" 相当（省略） | {"fixed": 3} / {"min": 2, "max": 5}。**v1 の期待値は 1 回の calculate() 呼び出し分** |
| context 各フィールド | BattleContext の既定値 | フィールド名は Swift/Kotlin の BattleContext と同名。bool は false、`defenderIsFullHP` のみ true、HP 比率は 1.0 |

### タグ規約（Python のスキップ判定に使用）

- カテゴリ: `basic` / `rounding` / `stats` / `context` / `weather` / `terrain` / `ability` / `item` / `special_move` / `mega` / `regression`
- 特性ケース: **`ability:<nameEn>`**（発動・非発動の両方に付与）
- アイテムケース: **`item:<nameEn>`**
- 機能タグ（スネークケース）: `double_battle` / `weather_override` / `skin` / `ruin` / `aura` / `paradox_boost` / `multi_hit` / `parental_bond` / `unaware` / `mold_breaker` / `half_berry` / `expert_belt` / `hp_dependent` / `weight_dependent` / `speed_dependent` / `rank_dependent` / `fixed_damage` / `psyshock` / `body_press` / `foul_play` / `weather_ball` / `terrain_pulse` / `flying_press` / `freeze_dry` / `knock_off` / `walls` / `critical` / `burn` / `rank` / `immunity` / `stab` 等
- Python (pokelabo-ai) は未実装機能をタグ単位で明示スキップする（`SUPPORTED_ABILITIES` 台帳との突合せ + `UNSUPPORTED_TAGS`）。スキップは pass と区別して件数報告し、黙って増やさない

## ベクターの取得（検証テスト側の共通仕様）

1. 環境変数 `POKELABO_DATA_DIR` があれば `$POKELABO_DATA_DIR/golden/damage`
2. なければ sibling checkout（`~/projects/pokelabo-data`）を探索
3. 見つからなければ「pokelabo-data が見つかりません。~/projects/pokelabo-data を checkout するか POKELABO_DATA_DIR を設定してください」で fail（silent skip 禁止）
4. `index.json` の `schemaVersion` が非対応なら fail

## 対象外（既存ユニットテストの担当）

- 連続技のヒット数合算 UI・HP% 読み・メガ切替 UI 等のアプリロジック
- データファイル（pokemon.json 等）の整合性検証

## ケース設計の注意（生成側向け）

- **HP 比率（attackerHPRatio / defenderHPRatio）を使うケースは、HP 実数値が比率で割り切れる種族値を選ぶ**
  （例: HP 種族値 105 → 実数値 180）。割り切れないと「比率を直接使う実装」と「現在HPに量子化してから
  比率を再計算する実装」で ±1 の差が出る（実装ドリフトではなくケース設計の問題）
- **ミューテーション確認**（補正値を故意に変えて検知テスト）をする場合、±1 の変異（5325→5324 等）は
  pokeRound の量子化以下で最終ダメージが変わらないことがある。明確に異なる補正値（5325→6144 等）を使う
