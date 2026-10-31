"""
Comprehensive Test Suite for Cyber Viper Application.
Tests:
- Database schema & operations
- High-score calculation logic
- Leaderboard ranking & sorting
- Mode filtering
- Static files integrity (HTML, CSS, JS)
"""

import os
import sys
import json
import database

def test_database_and_logic():
    print("[TEST 1] Initializing SQLite database...")
    database.init_db()
    database.clear_history()

    # Initial stats check
    stats0 = database.get_stats()
    assert stats0["total_games"] == 0, f"Expected 0 games, got {stats0['total_games']}"
    assert stats0["high_score"] == 0, f"Expected 0 high score, got {stats0['high_score']}"
    print("   -> Initial stats clean: OK")

    # Insert Game 1 (Normal score)
    print("[TEST 2] Inserting Game 1 (Pilot: Alice, Score: 50)...")
    rec1 = database.insert_game(
        player_name="Alice",
        game_mode="Classic",
        difficulty="Normal",
        score=50,
        apples_eaten=5,
        duration_seconds=20.5,
        result="Hit Wall"
    )
    assert rec1["id"] == 1
    assert rec1["is_new_high"] is True
    print("   -> Inserted Game 1, new high score verified: OK")

    # Insert Game 2 (Higher score)
    print("[TEST 3] Inserting Game 2 (Pilot: Bob, Score: 180)...")
    rec2 = database.insert_game(
        player_name="Bob",
        game_mode="Speed Rush",
        difficulty="Hard",
        score=180,
        apples_eaten=14,
        duration_seconds=42.0,
        result="Collided with Self"
    )
    assert rec2["id"] == 2
    assert rec2["is_new_high"] is True
    print("   -> Inserted Game 2, new high score verified: OK")

    # Insert Game 3 (Lower score)
    print("[TEST 4] Inserting Game 3 (Pilot: Charlie, Score: 90)...")
    rec3 = database.insert_game(
        player_name="Charlie",
        game_mode="Portal",
        difficulty="Normal",
        score=90,
        apples_eaten=9,
        duration_seconds=28.3,
        result="Collided with Self"
    )
    assert rec3["id"] == 3
    assert rec3["is_new_high"] is False
    print("   -> Inserted Game 3, not high score verified: OK")

    # Test Leaderboard Ordering
    print("[TEST 5] Checking Leaderboard Ordering...")
    leaderboard = database.get_leaderboard()
    assert len(leaderboard) == 3
    assert leaderboard[0]["player_name"] == "Bob"
    assert leaderboard[0]["score"] == 180
    assert leaderboard[1]["player_name"] == "Charlie"
    assert leaderboard[1]["score"] == 90
    assert leaderboard[2]["player_name"] == "Alice"
    assert leaderboard[2]["score"] == 50
    print("   -> Leaderboard ranked correctly: Bob (180) > Charlie (90) > Alice (50): OK")

    # Test History Filtering by Game Mode
    print("[TEST 6] Testing History filtering by Mode...")
    all_history = database.get_history()
    assert len(all_history) == 3

    speed_history = database.get_history(mode="Speed Rush")
    assert len(speed_history) == 1
    assert speed_history[0]["player_name"] == "Bob"

    portal_history = database.get_history(mode="Portal")
    assert len(portal_history) == 1
    assert portal_history[0]["player_name"] == "Charlie"
    print("   -> Mode filtering works correctly: OK")

    # Test Stats Aggregations
    print("[TEST 7] Testing Stats Aggregation...")
    stats = database.get_stats()
    assert stats["total_games"] == 3
    assert stats["high_score"] == 180
    assert stats["total_apples"] == 28
    print(f"   -> Stats verified: Total Games = {stats['total_games']}, High = {stats['high_score']}, Apples = {stats['total_apples']}: OK")

    # Test Static Files Integrity
    print("[TEST 8] Checking Frontend Static Assets...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")

    html_file = os.path.join(static_dir, "index.html")
    css_file = os.path.join(static_dir, "style.css")
    js_file = os.path.join(static_dir, "app.js")

    assert os.path.exists(html_file), "index.html is missing!"
    assert os.path.exists(css_file), "style.css is missing!"
    assert os.path.exists(js_file), "app.js is missing!"

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
        assert "<canvas id=\"gameCanvas\"" in html
        assert "CYBER VIPER" in html
        assert "historyTableBody" in html
        assert "leaderboardTableBody" in html

    with open(css_file, "r", encoding="utf-8") as f:
        css = f.read()
        assert "--neon-cyan" in css
        assert ".canvas-wrapper" in css

    with open(js_file, "r", encoding="utf-8") as f:
        js = f.read()
        assert "class GameEngine" in js
        assert "class SoundFX" in js
        assert "fetchStats" in js
        assert "saveGameRecord" in js

    print("   -> All frontend files present and validated: OK")

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 50)

if __name__ == "__main__":
    test_database_and_logic()
