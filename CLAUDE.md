# pokelabo-data

PokeLabo（iOS/Android）へ GitHub Pages 経由でゲームデータを配信するリポジトリ。
アプリは起動時に `manifest.json` の差分をみて `pokemon.json` / `moves.json` / `items.json` /
`abilities.json` / `regulations.json` / `usage_stats.json` を同期する。

## 更新ルール

- 全データ再取得: `python3 update.py`（PokeAPI から再取得するため**手修正が上書きされる**）
- JSON を手動編集した場合: **必ず `python3 update.py --manifest-only`**（manifest だけ更新して push）
- push が拒否されたらローカルが古い: `git fetch && git reset --hard origin/main` → 再コピー → `--manifest-only`

## golden/（ゴールデンテストベクター）

`golden/damage/*.json` はダメージ計算 3 実装（Swift/Kotlin/Python）のドリフト検知用テストベクター。

- **正本は iOS リポジトリの `tools/golden-gen`**。ここのファイルを手編集しない
- **`update.py` の対象外**（update.py を改修するときも golden/ に触れない）
- **アプリ配信の `manifest.json` に含めない**（アプリのリモート同期とは無関係）
- 再生成は iOS リポジトリで `scripts/generate_golden.sh`
- スキーマ・運用フローの詳細: `golden/SCHEMA.md`
