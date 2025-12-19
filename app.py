from flask import Flask, request, jsonify, render_template
import random

app = Flask(__name__)

# ---- Required Central Store (Dictionary) ----
LEADERBOARD = {}  # key: player name, value: dict of stats

# ---- Current 10-round game state ----
CURRENT_GAME = {
    "player1": None,
    "player2": None,
    "round": 0,
    "round_wins": {"player1": 0, "player2": 0},  # wins inside THIS 10-round game
    "locked_player1": False,  # for winner retention behavior
}

CHOICES = ("rock", "paper", "scissors")


def ensure_player(name: str) -> None:
    """Register player if missing (O(1) average dict access)."""
    if name not in LEADERBOARD:
        LEADERBOARD[name] = {"score": 0, "games_won": 0}


def rps_winner(p1_choice: str, p2_choice: str) -> int:
    """
    Returns:
      0 = tie
      1 = player1 wins
      2 = player2 wins
    """
    if p1_choice == p2_choice:
        return 0
    wins = {
        ("rock", "scissors"),
        ("scissors", "paper"),
        ("paper", "rock"),
    }
    return 1 if (p1_choice, p2_choice) in wins else 2


@app.get("/")
def home():
    return render_template("index.html")


# ---------- REST Endpoints (as required) ----------

@app.post("/api/player/register")
def api_player_register():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"error": "Player name is required"}), 400

    ensure_player(name)
    return jsonify({"ok": True, "player": {"name": name, **LEADERBOARD[name]}})


@app.post("/api/game/start")
def api_game_start():
    data = request.get_json(force=True)
    p1 = (data.get("player1") or "").strip()
    p2 = (data.get("player2") or "").strip()

    # Winner retention: if player1 is locked, ignore provided player1
    if CURRENT_GAME["locked_player1"] and CURRENT_GAME["player1"]:
        p1 = CURRENT_GAME["player1"]

    if not p1 or not p2:
        return jsonify({"error": "Both player1 and player2 are required"}), 400
    if p1 == p2:
        return jsonify({"error": "Players must be different"}), 400

    ensure_player(p1)
    ensure_player(p2)

    CURRENT_GAME.update({
        "player1": p1,
        "player2": p2,
        "round": 0,
        "round_wins": {"player1": 0, "player2": 0},
        # locked_player1 stays as-is; it becomes True after first finished game
        "locked_player1": CURRENT_GAME["locked_player1"],
    })

    return jsonify({
        "ok": True,
        "game": {
            "player1": CURRENT_GAME["player1"],
            "player2": CURRENT_GAME["player2"],
            "round": CURRENT_GAME["round"],
            "locked_player1": CURRENT_GAME["locked_player1"],
        }
    })


@app.post("/api/game/play_round")
def api_play_round():
    if not CURRENT_GAME["player1"] or not CURRENT_GAME["player2"]:
        return jsonify({"error": "Start a game first"}), 400
    if CURRENT_GAME["round"] >= 10:
        return jsonify({"error": "Game already finished. Start a new game."}), 400

    data = request.get_json(force=True)

    # You can accept player choices from UI; to keep it simple, default to random if missing.
    p1_choice = (data.get("p1_choice") or random.choice(CHOICES)).lower()
    p2_choice = (data.get("p2_choice") or random.choice(CHOICES)).lower()

    if p1_choice not in CHOICES or p2_choice not in CHOICES:
        return jsonify({"error": "Choices must be: rock, paper, scissors"}), 400

    winner = rps_winner(p1_choice, p2_choice)

    CURRENT_GAME["round"] += 1
    round_result = "tie"
    if winner == 1:
        CURRENT_GAME["round_wins"]["player1"] += 1
        round_result = "player1"
    elif winner == 2:
        CURRENT_GAME["round_wins"]["player2"] += 1
        round_result = "player2"

    # When 10 rounds complete, finalize game and update LEADERBOARD cumulative stats
    finished = CURRENT_GAME["round"] == 10
    game_winner = None

    if finished:
        p1 = CURRENT_GAME["player1"]
        p2 = CURRENT_GAME["player2"]
        p1_wins = CURRENT_GAME["round_wins"]["player1"]
        p2_wins = CURRENT_GAME["round_wins"]["player2"]

        # Example scoring: +1 cumulative score per round win (simple + clear)
        LEADERBOARD[p1]["score"] += p1_wins
        LEADERBOARD[p2]["score"] += p2_wins

        if p1_wins > p2_wins:
            LEADERBOARD[p1]["games_won"] += 1
            game_winner = p1
        elif p2_wins > p1_wins:
            LEADERBOARD[p2]["games_won"] += 1
            game_winner = p2
        else:
            game_winner = None  # tie game

        # Winner retention requirement: winner becomes locked player1 for next match
        if game_winner:
            CURRENT_GAME["player1"] = game_winner
            CURRENT_GAME["locked_player1"] = True
        else:
            # If tie, you can choose a rule; simplest: unlock so user can set both again.
            CURRENT_GAME["locked_player1"] = False

        CURRENT_GAME["player2"] = None  # require a new opponent next
        CURRENT_GAME["round"] = 10  # stays finished until restart

    return jsonify({
        "ok": True,
        "round": CURRENT_GAME["round"],
        "p1_choice": p1_choice,
        "p2_choice": p2_choice,
        "round_result": round_result,
        "round_wins": CURRENT_GAME["round_wins"],
        "finished": finished,
        "game_winner": game_winner,
        "locked_player1": CURRENT_GAME["locked_player1"],
        "next_player1": CURRENT_GAME["player1"],
    })


@app.get("/api/leaderboard")
def api_leaderboard():
    # Dict -> List[Dict] conversion for presentation (required)
    players = [
        {"name": name, "score": stats["score"], "games_won": stats["games_won"]}
        for name, stats in LEADERBOARD.items()
    ]

    # Two required sorted views
    by_name = sorted(players, key=lambda p: p["name"].lower())
    by_score = sorted(players, key=lambda p: p["score"], reverse=True)

    return jsonify({"by_name": by_name, "by_score": by_score})


if __name__ == "__main__":
    app.run(debug=True)
