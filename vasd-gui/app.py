from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import base64
from datetime import datetime, timedelta
from configparser import ConfigParser

conf = ConfigParser()
conf.read('config.ini')
days = int(conf.get("data_store", "no_of_days"))

app = Flask(__name__)

DB = "database.db"
IMAGE_FOLDER = "static/images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS vehicle_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            name TEXT,
            lane INTEGER,
            speed INTEGER,
            min_speed INTEGER,
            max_speed INTEGER,
            vehicle_class TEXT,
            violation TEXT,
            image_path TEXT,
            created_at TEXT
        )
    ''')

    conn.commit()
    conn.close()


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.json

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    image_data = data.get("image")
    image_path = ""

    # save base64 image
    if image_data:
        img_name = f"{int(now.timestamp())}.jpg"
        image_path = os.path.join(IMAGE_FOLDER, img_name)

        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_data))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        INSERT INTO vehicle_data (
            timestamp, name, lane, speed,
            min_speed, max_speed, vehicle_class,
            violation, image_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        data.get("name"),
        data.get("lane"),
        data.get("speed"),
        data.get("min_speed"),
        data.get("max_speed"),
        data.get("vehicle_class"),
        data.get("violation"),
        image_path,
        timestamp
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "saved"})


@app.route('/api/data', methods=['GET'])
def get_data():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # delete older than 7 days
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("SELECT image_path FROM vehicle_data WHERE created_at < ?", (cutoff_str,))
    rows = c.fetchall()

    for row in rows:
        image_path = row[0]   

        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"Error deleting {image_path}: {e}")

    c.execute("DELETE FROM vehicle_data WHERE created_at < ?", (cutoff_str,))
    conn.commit()

    # filter params
    from_time = request.args.get("from")
    to_time = request.args.get("to")

    query = "SELECT * FROM vehicle_data"
    params = []

    if from_time and to_time:
        query += " WHERE created_at BETWEEN ? AND ?"
        params.extend([from_time, to_time])

    query += " ORDER BY id DESC"

    c.execute(query, params)
    rows = c.fetchall()

    conn.close()

    result = []
    for row in rows:
        result.append({
            "timestamp": row[1],
            "name": row[2],
            "lane": row[3],
            "speed": row[4],
            "min_speed": row[5],
            "max_speed": row[6],
            "vehicle_class": row[7],
            "violation": row[8],
            "image": "/" + row[9] if row[9] else ""
        })

    return jsonify(result)

if __name__ == "__main__":
    init_db()

    app.run(debug=True)