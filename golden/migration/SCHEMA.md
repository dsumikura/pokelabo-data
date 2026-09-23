# 移行スナップショット（migration snapshots）

iOS（PokeLabo）から書き出したパーティ・ボックス・設定を他の実装で取り込むための JSON 契約。

- **契約の正本はこの文書**（`schemaVersion: 1`）
- **固定サンプルの正本は iOS の `PokeLaboTests/MigrationSnapshotSampleTests.swift`**。`samples/*.json` は手編集しない
- **アプリ配信用の `manifest.json` には含めない**（アプリのリモート同期とは無関係）
- **`update.py` の対象外**。update.py を改修するときもこのディレクトリに触れない

## ファイル構成

```
golden/migration/
├ SCHEMA.md
└ samples/
  ├ empty.json
  └ full.json
```

## スキーマ（schemaVersion 1）

### 構造

以下は説明用の例（省略表記あり）。完全な JSON は固定サンプルを参照する。


```json
{
  "schemaVersion": 1,
  "snapshotId": "9F1B6A2E-3C1D-4F0A-9B1E-000000000001",
  "exportedAt": "2026-09-14T03:04:05.678Z",
  "source": {
    "platform": "ios",
    "appVersion": "2.1.15",
    "build": "1",
    "dataManifestVersion": 42
  },
  "counts": { "parties": 1, "partyMembers": 2, "box": 1 },
  "parties": [
    {
      "id": "…UUID…",
      "name": "メインパーティ",
      "regulation": "M-C",
      "createdAt": "2026-09-01T10:00:00.000Z",
      "members": [
        {
          "id": "…UUID…",
          "orderIndex": 0,
          "pokemonId": 303,
          "megaIndex": -1,
          "formIndex": -1,
          "abilityIndex": 0,
          "itemId": 5,
          "moveIds": [9, null, 8, null],
          "evs": { "hp": 32, "attack": 32, "defense": 0, "spAttack": 0, "spDefense": 0, "speed": 2 },
          "natureModifiers": { "attack": 1.1, "defense": 1.0, "spAttack": 0.9, "spDefense": 1.0, "speed": 1.0 }
        }
      ]
    }
  ],
  "box": [
    {
      "id": "…UUID…",
      "addedAt": "2026-09-02T11:00:00.000Z",
      "pokemonId": 445,
      "megaIndex": 0,
      "formIndex": -1,
      "abilityIndex": 1,
      "itemId": null,
      "moveIds": [null, null, null, null],
      "evs": { "hp": 0, "attack": 0, "defense": 0, "spAttack": 0, "spDefense": 0, "speed": 0 },
      "natureModifiers": { "attack": 1.0, "defense": 1.0, "spAttack": 1.0, "spDefense": 1.0, "speed": 1.0 }
    }
  ],
  "settings": {
    "pokemonFilter": "M-C",
    "isDoubleBattle": false,
    "appearance": null,
    "partyTabSelection": "box",
    "lastShownReleaseNotesVersion": "2.1.14"
  },
  "calculatorState": { "attackerPokemonId": 115, "attackerMegaIndex": 0, "…": "…" }
}
```

### 規則

| 項目 | 規則 |
|---|---|
| キー順 | エンコーダの `sortedKeys` に従う（上の例は説明用の順序。実ファイルは辞書順） |
| `id` | UUID 文字列（大文字、ハイフン付き。`UUID().uuidString` の形式）。再書き出しで不変。RN 取込はこの `id` で冪等化する |
| 日時 | ISO 8601、UTC、ミリ秒 3 桁、`Z` 終端（`2026-09-14T03:04:05.678Z`）。`ISO8601DateFormatter` の `.withInternetDateTime` + `.withFractionalSeconds` |
| `moveIds` | 長さ固定 4。空き枠は `null` を **その位置に** 置く。前詰めしない。変化技 ID を含み得る（RN の計算用データは変化技を除外しているので、取込側は `includeStatus` 相当の技マスタで解決する） |
| `itemId` | `null` = なし |
| `natureModifiers` | 0.9 / 1.0 / 1.1 の 5 値をそのまま。単一の性格に一致しない組み合わせもあり得る。性格名への写像は取込側の責務 |
| `megaIndex` / `formIndex` | -1 = 通常。添字は書き出し時点のポケモンマスタの配列順（`dataManifestVersion` で識別） |
| `settings.*` | UserDefaults に未書き込みなら `null`。既定値で埋めない。`appearance` は `system` / `light` / `dark`、`partyTabSelection` は `party` / `box` |
| `calculatorState` | iOS の `CalculatorPersistedState` を JSON 化した生オブジェクト、または `null`。キー名は iOS の実装名で、この契約では不透明（opaque）な値として扱う。取込側の変換は RN の責務。フィールド一覧は SCHEMA.md に参考として列挙する |
| `counts` | 各配列の要素数。`partyMembers` は全パーティのメンバー合計。取込側は配列長との一致を検証する |
| 含めないもの | 購入キャッシュ、広告同意、SwiftData 管理列 |
| 互換規則 | 将来はキー追加のみ（既存キーの削除・型変更をしない）。破壊的変更は `schemaVersion` を上げる |

## 取込側の規約

- パーティ・メンバー・ボックスの **`id` で冪等化する**。`snapshotId` は書き出しごとに変わるため、レコードの識別に使わない
- `counts.parties == parties.length`、`counts.partyMembers == 全 parties の members.length の合計`、`counts.box == box.length` を検証する
- **未知の `schemaVersion` は拒否**する。対応バージョン内の未知キーは無視する
- `moveIds` は長さ 4。`null` の位置を保持し、**変化技を含む技マスタ**で ID を解決する
- `natureModifiers` は 5 値をそのまま保持する。性格名への写像は取込側の責務で、単一の性格に一致しない組み合わせも受け入れる
- **v2.1.15 未経由のスナップショットには旧 ID 10176 / 10226 が残り得る**。取込側でも `[10176: 10186, 10226: 10191]` を適用する。対象はメンバー・ボックスの `pokemonId` と計算状態の `attackerPokemonId` / `defenderPokemonId`
- パーティは `createdAt` 昇順、同値は `id` 文字列昇順。メンバーは `orderIndex` 昇順。ボックスは `addedAt` 昇順、同値は `id` 文字列昇順で書き出す
- スナップショットの optional 値は明示的な `null`。ただし以下の生の `calculatorState` 内は例外（nil はキー欠落）

## calculatorState のフィールド一覧（参考）

`CalculatorPersistedState` の生 JSON オブジェクト、または `null`。以下は iOS v2.1.15 の全プロパティ。
Swift 型の `Int` / `Double` は JSON 数値、`Bool` は真偽値。**`?` は optional で、nil のときはキー自体が欠落する**。
スナップショット本体の null 規約とは区別する。データ変換は取込側の責務。

| フィールド | Swift 型 |
|---|---|
| `attackerPokemonId` | `Int?` |
| `attackerMegaIndex` | `Int` |
| `attackerFormIndex` | `Int` |
| `attackerLevel` | `Int` |
| `attackerAttackNatureModifier` | `Double` |
| `attackerSpAttackNatureModifier` | `Double` |
| `attackerEVAttack` | `Int` |
| `attackerEVSpAttack` | `Int` |
| `attackerAttackRank` | `Int` |
| `attackerSpAttackRank` | `Int` |
| `attackerAbilityIndex` | `Int` |
| `attackerAbilityEnabled` | `Bool` |
| `attackerItemId` | `Int?` |
| `isBurned` | `Bool` |
| `attackerEVDefense` | `Int` |
| `attackerDefenseNatureModifier` | `Double` |
| `attackerDefenseRank` | `Int` |
| `attackerHPRatio` | `Double` |
| `defenderHPRatio` | `Double` |
| `defenderPokemonId` | `Int?` |
| `defenderMegaIndex` | `Int` |
| `defenderFormIndex` | `Int` |
| `defenderLevel` | `Int` |
| `defenderAbilityIndex` | `Int` |
| `defenderAbilityEnabled` | `Bool` |
| `defenderItemId` | `Int?` |
| `defenderDefenseNatureModifier` | `Double` |
| `defenderSpDefenseNatureModifier` | `Double` |
| `defenderEVHP` | `Int` |
| `defenderEVDefense` | `Int` |
| `defenderEVSpDefense` | `Int?` |
| `defenderDefenseRank` | `Int` |
| `defenderSpDefenseRank` | `Int` |
| `defenderEVAttack` | `Int` |
| `defenderAttackNatureModifier` | `Double` |
| `defenderAttackRank` | `Int` |

## 固定サンプルと再生成

- `empty.json`: パーティ・ボックスが空、設定 5 キーと計算状態は `null`
- `full.json`: パーティ 2 件（6 + 1 体）、ボックス 3 体。技枠 null 混在、単一性格に一致しない倍率、メガ、フォーム、もちもの null、設定 5 キー、計算状態を含む
- UUID・日時・source はテスト内の固定値。source は `ios` / `2.1.15` / `1` / manifest `42`
- エンコーダは `MigrationSnapshotCoding.makeEncoder()`（`sortedKeys` / `prettyPrinted` / `withoutEscapingSlashes`）。同じ入力は同じバイト列になる
- サンプルの生成元は iOS の **`MigrationSnapshotSampleTests`**。`MigrationSnapshotTestFixtures` を共用する。計算状態は固定の `CalculatorPersistedState` を `JSONEncoder` → `JSONValue` で同梱する
- 通常の T601 / T602 は保存済みサンプルとのバイト一致を検証する。T603 は契約規則、T604 は一時ディレクトリで書き出し経路を検証する

再生成は iOS リポジトリで `POKELABO_MIGRATION_WRITE_SAMPLES=1` をテストプロセスに渡す。
`xcodebuild` 経由では `TEST_RUNNER_` を付ける（シミュレータ名・OS は実行環境に合わせる）。

```bash
TEST_RUNNER_POKELABO_MIGRATION_WRITE_SAMPLES=1 \
TEST_RUNNER_POKELABO_DATA_DIR="$HOME/projects/pokelabo-data" \
xcodebuild test -project PokeLabo.xcodeproj -scheme PokeLabo \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.6' \
  -only-testing:PokeLaboTests/MigrationSnapshotSampleTests
```

生成後は `TEST_RUNNER_POKELABO_MIGRATION_WRITE_SAMPLES` を外して同じテストを実行し、バイト一致を確認する。
通常の検証・CI では書き出しモードを設定しない。生成時は `samples/` ディレクトリも作成する。

### pokelabo-data の解決

1. `POKELABO_DATA_DIR` があればそこを使用
2. なければ iOS テストソースの `#filePath` を基準に sibling checkout の `pokelabo-data` を使用（通常は `~/projects/pokelabo-data`）
3. `GoldenVectorTests` と同じく `golden/damage/index.json` の存在で checkout を確認し、なければ次のエラーで fail（silent skip 禁止）

```
pokelabo-data が見つかりません (<path>)。~/projects/pokelabo-data を checkout するか POKELABO_DATA_DIR を設定してください
```

比較対象は `golden/migration/samples/{empty,full}.json`。通常モードでファイルがなければ読み取りエラーで fail する。
