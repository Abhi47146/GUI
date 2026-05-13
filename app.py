from multiprocessing import shared_memory
import numpy as np
import cv2
import os
import sqlite3
from configparser import ConfigParser

from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from passlib.context import CryptContext

conf = ConfigParser()
conf.read('config.ini')
STREAMS = conf.get("Junctions", "scns").split(',')
IP = conf.get("api", "ip")

app = Flask(__name__)
app.secret_key = "your_secret_key"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

DATABASE = "users.db"
BASE_FOLDER = "static/images"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

if not os.path.exists(DATABASE):
    init_db()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_conn():
    return sqlite3.connect(DATABASE)

@app.route("/signup", methods=["POST"])
def signup():
    email = request.form.get("email")
    password = request.form.get("password")

    hashed_password = pwd_context.hash(password)

    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (email, hashed_password)
            )
            conn.commit()
        return redirect("/")
    except sqlite3.IntegrityError:
        return "User already exists"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("index_sign.html")

    email = request.form.get("email")
    password = request.form.get("password")

    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

    if user and pwd_context.verify(password, user[0]):
        session["user"] = email
        return redirect("/home")
    else:
        return render_template("index_sign.html", error="Invalid Credentials")

@app.route("/logout")
def logout():
    return redirect("/")

shared_blocks = {}
shared_cache = {}

def get_shm_array(stream_id):
    name = f"shm_{stream_id}"

    if stream_id in shared_cache:
        return shared_cache[stream_id]

    shm = shared_memory.SharedMemory(name=name)
    array = np.ndarray((640, 640, 3), dtype=np.uint8, buffer=shm.buf)

    shared_cache[stream_id] = (shm, array)
    print("Connected to SHM:", name)

    return shared_cache[stream_id]

for stream_id in STREAMS:
    name = f"shm_{stream_id}"
    size = 640 * 640 * 3

    try:
        shm = shared_memory.SharedMemory(name=name, create=True, size=size)
        print("Created SHM:", name)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=name)
        print("Attached existing SHM:", name)

    shared_blocks[stream_id] = np.ndarray((640, 640, 3), dtype=np.uint8, buffer=shm.buf)

@socketio.on("connect")
def connect():
    print("Client connected")

@socketio.on("stream")
def stream(data):
    stream_id = data["stream_id"]

    shm, frame_array = get_shm_array(stream_id)

    while True:
        safe_frame = frame_array.copy()
        _, buffer = cv2.imencode('.jpg', safe_frame)

        emit("frame", buffer.tobytes())
        socketio.sleep(0.03)

# ---------------- ROUTES ----------------
@app.route("/home")
def home():
    return render_template("dashboard.html", streams=STREAMS, ip=IP)

@app.route("/view1")
def live_grid():
    return render_template("live.html", stream_id="ALL", streams=STREAMS)


@app.route("/view1/<stream_id>")
def video_feed(stream_id):
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <!-- Tailwind -->
        <script src="https://cdn.tailwindcss.com"></script>

        <!-- Font -->
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap" rel="stylesheet">

        <style>
            body {{
                font-family: 'Manrope', sans-serif;
            }}
        </style>
    </head>

    <body class="bg-[#0b1326] text-white">

        <!-- Center Container -->
        <div class="min-h-screen flex flex-col items-center justify-center px-4">

            <!-- Camera Card -->
            <div class="w-full max-w-4xl bg-[#171f33] rounded-xl shadow-xl overflow-hidden">

                <!-- Header -->
                <div class="p-4 border-b border-gray-700 flex items-center justify-between">
                    <h2 class="text-lg font-bold tracking-wide">
                         Camera: {stream_id}
                    </h2>
                    <span class="text-xs text-green-400 flex items-center gap-1">
                        <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                        LIVE
                    </span>
                </div>

                <!-- Video -->
                <div class="flex items-center justify-center bg-black">
                    <img id="video" class="w-full max-h-[70vh] object-contain"/>
                </div>

            </div>
        </div>

        <!-- Socket -->
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>

        <script>
        const socket = io();

        socket.emit("stream", {{stream_id: "{stream_id}"}});

        socket.on("frame", (data) => {{
            const blob = new Blob([data], {{ type: "image/jpeg" }});
            document.getElementById("video").src = URL.createObjectURL(blob);
        }});
        </script>

    </body>
    </html>
    """

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)