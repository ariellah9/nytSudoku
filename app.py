from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", 5000))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    raw_name = str(data.get("name")).strip()
    name = raw_name.lower().capitalize()
    time = float(data.get("time"))
    level = str(data.get("level"))

    multiple = {"easy": 1.5, "medium": 1.0, "hard": 0.5}.get(level)
    if multiple is None:
        return jsonify({"error": "Invalid level"}), 400

    adjusted_time = time * multiple

    # Fetch player by canonical key
    response = supabase.table("scores").select("*").eq("name", name).execute()
    player = response.data[0] if response.data else None

    if not player:
        # Insert new player, storing lowercase in `name`
        new_player = {
            "name": name,           
            "overall_avg": adjusted_time,
            "overall_games": 1,
            "easy_avg": time if level=="easy" else 0,
            "easy_games": 1 if level=="easy" else 0,
            "medium_avg": time if level=="medium" else 0,
            "medium_games": 1 if level=="medium" else 0,
            "hard_avg": time if level=="hard" else 0,
            "hard_games": 1 if level=="hard" else 0
        }
        supabase.table("scores").insert(new_player).execute()
    else:
        # Update stats
        overall_games = player["overall_games"] + 1
        overall_avg = ((player["overall_avg"] * player["overall_games"]) + adjusted_time) / overall_games

        level_games_key = f"{level}_games"
        level_avg_key = f"{level}_avg"
        level_games = player[level_games_key] + 1
        level_avg = ((player[level_avg_key] * player[level_games_key]) + time) / level_games

        supabase.table("scores").update({
            "name": name,  
            "overall_avg": overall_avg,
            "overall_games": overall_games,
            level_avg_key: level_avg,
            level_games_key: level_games
        }).eq("name", name).execute()

    return jsonify({"message": "Submission received"}), 200

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    response = supabase.table("scores").select("*").execute()
    data = response.data or []

    # Sort ascending, putting missing overall_avg at the end
    data.sort(key=lambda x: x["overall_avg"] if x.get("overall_avg") is not None else float('inf'))

    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))