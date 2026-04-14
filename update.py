#!/usr/bin/env python3
"""
pokelabo-data 更新スクリプト
Usage:
  python3 update.py                    # 全データ再取得 + manifest更新 + commit & push
  python3 update.py --manifest-only    # manifestのみ更新（手動でJSON編集した場合）
  python3 update.py --no-push          # commit まで（pushしない）

⚠ 注意: PokeAPIはリージョナルフォーム（アローラ等）の覚える技を
        通常フォームにも混入させて返します。Champions準拠の正確な技は
        PokeLabo側の `python3 scripts/fetch_gamewith_moves.py` で取得し、
        生成された pokemon.json をこのリポジトリにコピーしてください。
        運用例:
          cd ~/projects/PokeLabo
          python3 scripts/fetch_gamewith_moves.py
          cp PokeLabo/Resources/pokemon.json ~/projects/pokelabo-data/pokemon.json
          cd ~/projects/pokelabo-data
          python3 update.py --manifest-only
"""

import json
import hashlib
import datetime
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

API_BASE = "https://pokeapi.co/api/v2"
DATA_DIR = Path(__file__).parent

MEGA_CAPABLE_IDS = {
    3, 6, 9, 15, 18, 65, 80, 94, 115, 127, 130, 142, 150,
    181, 208, 212, 214, 229, 248, 254, 257, 260, 282, 302,
    303, 306, 308, 310, 319, 323, 334, 354, 359, 362, 373,
    376, 380, 381, 384, 428, 445, 448, 460, 475, 531, 719,
}

VALID_TYPES = {
    "normal", "fire", "water", "grass", "electric", "ice",
    "fighting", "poison", "ground", "flying", "psychic",
    "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy",
}


def get_japanese_name(names: list[dict]) -> str:
    for n in names:
        if n["language"]["name"] == "ja":
            return n["name"]
    return ""


def fetch_json(url: str) -> dict:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PokeLabo/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError):
            if attempt < 2:
                time.sleep(2)
                continue
            raise


def fetch_list(endpoint: str) -> list[dict]:
    return fetch_json(f"{API_BASE}/{endpoint}?limit=2000").get("results", [])


# ==============================
# ポケモン
# ==============================

def determine_final_evolutions() -> set[int]:
    print("最終進化ポケモンを特定中...")
    species_list = fetch_list("pokemon-species")
    total = len(species_list)
    parent_ids: set[int] = set()
    all_ids: set[int] = set()
    baby_ids: set[int] = set()

    for i, sp in enumerate(species_list):
        sp_id = int(sp["url"].rstrip("/").split("/")[-1])
        all_ids.add(sp_id)
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{total}]...")
        try:
            data = fetch_json(sp["url"])
        except Exception:
            continue
        evolves_from = data.get("evolves_from_species")
        if evolves_from:
            parent_id = int(evolves_from["url"].rstrip("/").split("/")[-1])
            parent_ids.add(parent_id)
        if data.get("is_baby"):
            baby_ids.add(sp_id)
        time.sleep(0.35)

    final_ids = all_ids - parent_ids - baby_ids
    print(f"  最終進化: {len(final_ids)}匹")
    return final_ids


def fetch_mega_form(mega_name: str) -> dict | None:
    try:
        data = fetch_json(f"{API_BASE}/pokemon/{mega_name}")
    except Exception:
        return None

    types = [t["type"]["name"] for t in sorted(data["types"], key=lambda x: x["slot"])]
    stat_map = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    base_stats = {
        "hp": stat_map.get("hp", 0), "attack": stat_map.get("attack", 0),
        "defense": stat_map.get("defense", 0), "spAttack": stat_map.get("special-attack", 0),
        "spDefense": stat_map.get("special-defense", 0), "speed": stat_map.get("speed", 0),
    }
    ability_data = {"id": 0, "name": "不明", "nameEn": "Unknown", "effects": []}
    for a in data["abilities"]:
        try:
            ab = fetch_json(a["ability"]["url"])
            ability_data = {
                "id": ab["id"],
                "name": get_japanese_name(ab.get("names", [])) or ab["name"],
                "nameEn": ab["name"].replace("-", " ").title(), "effects": [],
            }
            break
        except Exception:
            pass

    if mega_name.endswith("-mega-x"):
        display = "メガシンカ X"
    elif mega_name.endswith("-mega-y"):
        display = "メガシンカ Y"
    elif mega_name.endswith("-mega-z"):
        display = "メガシンカ Z"
    else:
        display = "メガシンカ"

    return {
        "name": display, "types": types, "baseStats": base_stats,
        "ability": ability_data, "megaStone": mega_name,
        "spriteId": data["id"],
    }


def fetch_pokemon(pokemon_id: int) -> dict | None:
    try:
        data = fetch_json(f"{API_BASE}/pokemon/{pokemon_id}")
        species = fetch_json(f"{API_BASE}/pokemon-species/{pokemon_id}")
    except Exception:
        return None

    ja_name = get_japanese_name(species.get("names", []))
    en_name = data["name"].capitalize()
    types = [t["type"]["name"] for t in sorted(data["types"], key=lambda x: x["slot"])]
    stat_map = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    base_stats = {
        "hp": stat_map.get("hp", 0), "attack": stat_map.get("attack", 0),
        "defense": stat_map.get("defense", 0), "spAttack": stat_map.get("special-attack", 0),
        "spDefense": stat_map.get("special-defense", 0), "speed": stat_map.get("speed", 0),
    }
    abilities = []
    for a in data["abilities"]:
        try:
            ab = fetch_json(a["ability"]["url"])
            abilities.append({
                "id": ab["id"],
                "name": get_japanese_name(ab.get("names", [])) or ab["name"],
                "nameEn": ab["name"].replace("-", " ").title(), "effects": [],
            })
        except Exception:
            pass
        time.sleep(0.2)

    learnable_move_ids = []
    for m in data.get("moves", []):
        parts = m.get("move", {}).get("url", "").rstrip("/").split("/")
        if parts:
            try:
                learnable_move_ids.append(int(parts[-1]))
            except ValueError:
                pass

    mega_evolutions = []
    if pokemon_id in MEGA_CAPABLE_IDS:
        for v in species.get("varieties", []):
            pn = v.get("pokemon", {}).get("name", "")
            if pn.endswith("-mega") or pn.endswith("-mega-x") \
               or pn.endswith("-mega-y") or pn.endswith("-mega-z"):
                mega = fetch_mega_form(pn)
                if mega:
                    mega_evolutions.append(mega)

    return {
        "id": pokemon_id, "name": ja_name or en_name, "nameEn": en_name,
        "types": types, "baseStats": base_stats, "abilities": abilities,
        "weight": data["weight"] / 10.0, "megaEvolutions": mega_evolutions,
        "forms": [], "learnableMoveIds": sorted(set(learnable_move_ids)),
    }


# ==============================
# 技
# ==============================

def fetch_move(move_id: int) -> dict | None:
    try:
        data = fetch_json(f"{API_BASE}/move/{move_id}")
    except Exception:
        return None
    if data.get("type") is None:
        return None
    move_type = data["type"]["name"]
    if move_type not in VALID_TYPES:
        return None

    ja_name = get_japanese_name(data.get("names", []))
    category_map = {"physical": "physical", "special": "special", "status": "status"}
    category = category_map.get(data["damage_class"]["name"], "status") if data.get("damage_class") else "status"

    return {
        "id": data["id"],
        "name": ja_name or data["name"].replace("-", " ").title(),
        "nameEn": data["name"].replace("-", " ").title(),
        "type": move_type, "category": category,
        "power": data.get("power"), "accuracy": data.get("accuracy"),
        "pp": data.get("pp") or 5, "priority": data.get("priority") or 0,
        "flags": {
            "isContact": False, "isSound": False, "isPunch": False,
            "isBite": False, "isSlicing": False, "isBullet": False, "isWind": False,
        },
        "powerType": "fixed", "hitCount": "single",
    }


# ==============================
# Manifest
# ==============================

def update_manifest():
    current = {}
    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            current = json.load(f)

    files = {}
    for name in ["pokemon", "moves", "items"]:
        path = DATA_DIR / f"{name}.json"
        if path.exists():
            with open(path, "rb") as f:
                data = f.read()
                files[name] = {"hash": hashlib.sha256(data).hexdigest(), "size": len(data)}

    manifest = {
        "version": current.get("version", 0) + 1,
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": files,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest.json updated (version {manifest['version']})")


# ==============================
# Main
# ==============================

def main():
    manifest_only = "--manifest-only" in sys.argv
    no_push = "--no-push" in sys.argv

    if not manifest_only:
        # ポケモン取得
        final_ids = determine_final_evolutions()
        sorted_ids = sorted(final_ids)
        print(f"\n{len(sorted_ids)}匹のポケモンを取得中...")
        pokemon_list = []
        for i, pid in enumerate(sorted_ids):
            if (i + 1) % 20 == 0 or i == 0:
                print(f"  [{i+1}/{len(sorted_ids)}] #{pid}...")
            result = fetch_pokemon(pid)
            if result:
                pokemon_list.append(result)
            time.sleep(0.35)
        pokemon_list.sort(key=lambda p: p["id"])
        with open(DATA_DIR / "pokemon.json", "w", encoding="utf-8") as f:
            json.dump(pokemon_list, f, ensure_ascii=False, indent=2)
        print(f"  Saved {len(pokemon_list)} Pokemon")

        # 技取得
        move_list_raw = fetch_list("move")
        move_ids = sorted(int(m["url"].rstrip("/").split("/")[-1]) for m in move_list_raw)
        print(f"\n{len(move_ids)}技を取得中...")
        move_list = []
        for i, mid in enumerate(move_ids):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"  [{i+1}/{len(move_ids)}] #{mid}...")
            result = fetch_move(mid)
            if result:
                move_list.append(result)
            time.sleep(0.35)
        move_list.sort(key=lambda m: m["id"])
        with open(DATA_DIR / "moves.json", "w", encoding="utf-8") as f:
            json.dump(move_list, f, ensure_ascii=False, indent=2)
        print(f"  Saved {len(move_list)} Moves")

    # manifest更新
    update_manifest()

    # git commit & push
    subprocess.run(["git", "add", "-A"], cwd=DATA_DIR)
    subprocess.run(["git", "commit", "-m", "Data update"], cwd=DATA_DIR)
    if not no_push:
        subprocess.run(["git", "push"], cwd=DATA_DIR)
        print("\nPushed! GitHub Pagesに数分で反映されます。")
    else:
        print("\nCommitted (push skipped)")


if __name__ == "__main__":
    main()
