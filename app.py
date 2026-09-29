import configparser
import os
import socket
import sqlite3
from multiprocessing import resource_tracker, shared_memory
from urllib.parse import urlparse

import cv2
import numpy as np
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit
from passlib.context import CryptContext

CONFIG_FILE = "config.ini"

def load_config():
    config = configparser.ConfigParser(
        inline_comment_prefixes=('#', ';'),
        comment_prefixes=('#', ';')
    )
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config

def save_config(config):
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def check_stream_online(stream_url, timeout=0.5):
    
    if not stream_url:
        return False

    # 1. Handle RTSP / HTTP / HTTPS streams
    if stream_url.startswith(("rtsp://", "http://", "https://")):
        try:
            parsed = urlparse(stream_url)
            host = parsed.hostname
            port = parsed.port or (554 if parsed.scheme == "rtsp" else 80)

            if not host:
                return False

            # Fast TCP socket ping
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (TimeoutError, OSError):
            return False

    # 2. Handle local video files (e.g. .mp4 / .avi)
    elif os.path.exists(stream_url):
        return True

    return False

def get_streams_list():
    config = load_config()
    streams = []
    
    system_sections = ["api", "data_cleanup", "frame_size", "video_display", "tis", "GUI", "camera_scn"]
    
    if config.has_section("camera_scn") and config.has_option("camera_scn", "scns"):
        raw_scns = config.get("camera_scn", "scns")
        camera_scns = [
            s.strip() for s in raw_scns.split(",") 
            if s.strip() and s.strip() not in system_sections
        ]
        
        for scn in camera_scns:
            if config.has_section(scn):
                stream_url = config.get(scn, "stream", fallback="")
                tp_ip = config.get(scn, "third_party_ip", fallback="")
                tp_port = config.get(scn, "third_party_port", fallback="")
                
                zones = {
                    k: v for k, v in config.items(scn) 
                    if k.startswith("zone_dimensions_")
                }
                
                is_online = check_stream_online(stream_url)
                streams.append({
                    "scn": scn,
                    "url": stream_url,
                    "third_party_ip": tp_ip,
                    "third_party_port": tp_port,
                    "zones": zones,
                    "is_online": is_online,
                })

    return streams

def update_camera_in_config(old_scn, new_scn, stream_url, port="1233"):
    """
    Updates or adds camera details in config.ini while preserving 
    unrelated sections (like data_cleanup) and extra keys intact.
    """
    config = load_config()
    
    # Preserve existing camera keys if updating
    existing_items = {}
    if old_scn and config.has_section(old_scn):
        existing_items = dict(config.items(old_scn))
        if old_scn != new_scn:
            config.remove_section(old_scn)
            
    if not config.has_section(new_scn):
        config.add_section(new_scn)
        
    # Re-apply non-GUI keys if any existed
    for k, v in existing_items.items():
        config.set(new_scn, k, v)
        
    # Only update parameters edited from GUI
    config.set(new_scn, "stream", stream_url)
    config.set(new_scn, "port", port)
    
    # Safely update [Junctions] scns parameter without removing system sections like data_cleanup
    if config.has_section("camera_scn") and config.has_option("camera_scn", "scns"):
        raw_scns = [s.strip() for s in config.get("camera_scn", "scns").split(",") if s.strip()]
        
        # Replace or add the new camera SCN in the scns list
        if old_scn in raw_scns:
            idx = raw_scns.index(old_scn)
            raw_scns[idx] = new_scn
        elif new_scn not in raw_scns:
            raw_scns.append(new_scn)
            
        config.set("camera_scn", "scns", ",".join(raw_scns))
        
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

def sync_junctions_key(config):
    
    # System sections that must NEVER be written into the 'scns' camera list
    system_sections = ["api", "data_cleanup", "frame_size", "video_display", "tis", "GUI", "camera_scn"]
    
    # Filter out system sections
    camera_sections = [
        section for section in config.sections() 
        if section not in system_sections
    ]
    
    if not config.has_section("camera_scn"):
        config.add_section("camera_scn")
        
    config.set("camera_scn", "scns", ",".join(camera_sections))

def generate_raw_stream(stream_url, width=None, height=None):
    """Captures directly from RTSP URL or MP4 File Path using non-blocking FFmpeg options."""
    if not stream_url:
        return

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;tcp|timeout;2000000|stimeout;2000000"
    )

    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                
                break

            if width and height:
                frame = cv2.resize(frame, (width, height))

            _, buffer = cv2.imencode(".jpg", frame)
            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
    finally:
        cap.release()

conf = load_config()
IP = conf.get("api", "ip", fallback="127.0.0.1")

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

if not os.path.exists(DATABASE):
    init_db()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_conn():
    return sqlite3.connect(DATABASE)

# ---------------- AUTH ROUTES ----------------

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
    session.clear()
    return redirect("/")

# ---------------- SHARED MEMORY & STREAMING ----------------

shared_cache = {}

def get_shm_array(stream_id):
    name = f"result_shm_{stream_id}"

    if stream_id in shared_cache:
        return shared_cache[stream_id]

    shm = shared_memory.SharedMemory(name=name)
    resource_tracker.unregister(shm._name, "shared_memory")

    array = np.ndarray((640, 640, 3), dtype=np.uint8, buffer=shm.buf)
    shared_cache[stream_id] = (shm, array)
    print("Connected to SHM safely without ownership tracking:", name)

    return shared_cache[stream_id]

@socketio.on("stream")
def stream(data):
    stream_id = data["stream_id"]
    try:
        shm, frame_array = get_shm_array(stream_id)
    except Exception as e:
        print(f"Error accessing SHM for {stream_id}: {e}")
        return

    current_sid = request.sid
    print(f"Started streaming session for {stream_id} on SID: {current_sid}")

    while current_sid in socketio.server.manager.rooms.get('/', {}):
        try:
            safe_frame = frame_array.copy()
            _, buffer = cv2.imencode('.jpg', safe_frame)
            emit("frame", buffer.tobytes())
            socketio.sleep(0.03)
        except Exception as e:
            print(f"Streaming anomaly detected on SID {current_sid}: {e}")
            break

    print(f"Cleaned up background loop thread for SID: {current_sid}.")

# ---------------- DASHBOARD & CAMERA MANAGEMENT ----------------

@app.route("/home")
def home():
    # Extract only the scn string from each stream dictionary
    scns_only = [stream["scn"] for stream in get_streams_list()]
    return render_template("dashboard.html", streams=scns_only, ip=IP)

@app.route("/camera-management")
def camera_management():
    streams = get_streams_list()
    return render_template("camera_management.html", streams=streams)

@app.route("/add_camera", methods=["POST"])
def add_camera():
    scn = request.form.get("scn", "").strip()
    stream_link = request.form.get("stream", "").strip()
    third_party_ip = request.form.get("third_party_ip", "").strip()
    third_party_port = request.form.get("third_party_port", "").strip()

    if scn and stream_link:
        config = load_config()
        if not config.has_section(scn):
            config.add_section(scn)
            
        config.set(scn, "stream", stream_link)
        if third_party_ip:
            config.set(scn, "third_party_ip", third_party_ip)
        if third_party_port:
            config.set(scn, "third_party_port", third_party_port)
        config.set(scn, "debug", "False")
        config.set(scn, "result_storage_path", "None")
        sync_junctions_key(config)
        save_config(config)

    return redirect(url_for("camera_management"))

@app.route("/edit_camera", methods=["POST"])
def edit_camera():
    old_scn = request.form.get("old_scn", "").strip()
    scn = request.form.get("scn", "").strip()
    stream_link = request.form.get("stream", "").strip()
    third_party_ip = request.form.get("third_party_ip", "").strip()
    third_party_port = request.form.get("third_party_port", "").strip()

    config = load_config()
    if config.has_section(old_scn):
        # Preserve non-GUI items (like existing zone dimensions)
        existing_items = dict(config.items(old_scn))
        if old_scn != scn:
            config.remove_section(old_scn)

        if not config.has_section(scn):
            config.add_section(scn)

        for k, v in existing_items.items():
            config.set(scn, k, v)

        # Update GUI fields with exact target keys in config.ini
        config.set(scn, "stream", stream_link)
        config.set(scn, "third_party_ip", third_party_ip)
        config.set(scn, "third_party_port", third_party_port)

        sync_junctions_key(config)
        save_config(config)

    return redirect(url_for("camera_management"))

@app.route("/delete", methods=["POST"])
def delete_camera():
    data = request.get_json() or {}
    scn = data.get("scn")
    config = load_config()
    if scn and config.has_section(scn):
        config.remove_section(scn)
        sync_junctions_key(config)
        save_config(config)
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 400

@app.route("/camera-setup/<scn>")
def camera_setup(scn):
    config = load_config()
    if not config.has_section(scn):
        return redirect(url_for("camera_management"))

    stream_url = config.get(scn, "stream", fallback="")
    zones = {
        k: v for k, v in config.items(scn) if k.startswith("zone_dimensions_")
    }

    # Fetch dynamic frame dimensions from [frame_size] section
    frame_width = config.getint("frame_size", "width", fallback=640)
    frame_height = config.getint("frame_size", "height", fallback=480)

    return render_template(
        "camera_setup.html",
        scn=scn,
        stream_url=stream_url,
        zones=zones,
        frame_width=frame_width,
        frame_height=frame_height,
    )

@app.route("/video_feed/<scn>")
def direct_video_feed(scn):
    config = load_config()
    if config.has_section(scn):
        stream_url = config.get(scn, "stream", fallback="")
        if stream_url:
            # Read width and height from [frame_size]
            frame_width = config.getint("frame_size", "width", fallback=640)
            frame_height = config.getint("frame_size", "height", fallback=480)

            return Response(
                generate_raw_stream(
                    stream_url, width=frame_width, height=frame_height
                ),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )
    return "Stream unavailable", 404

@app.route("/save_zones", methods=["POST"])
def save_zones():
    data = request.get_json() or {}
    scn = data.get("scn")
    zones = data.get("zones", {})

    config = load_config()
    
    if config.has_section(scn):
        # 1. Remove old zone dimensions under this camera section
        for key in list(config[scn].keys()):
            if key.startswith("zone_dimensions_"):
                config.remove_option(scn, key)

        # 2. Add new zone dimension parameters
        for zone_key, coords in zones.items():
            config.set(scn, zone_key, coords)

        # 3. Save config file without overwriting other system sections (like data_cleanup)
        with open(CONFIG_FILE, "w") as configfile:
            config.write(configfile)

        return jsonify({"status": "success"}), 200

    return jsonify({"status": "error"}), 400

@app.route("/view1")
def live_grid():
    scns_only = [stream["scn"] for stream in get_streams_list()]
    return render_template("live.html", stream_id="ALL", streams=scns_only)

@app.route("/view1/<stream_id>")
def video_feed(stream_id):
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>body {{ font-family: 'Manrope', sans-serif; }}</style>
    </head>
    <body class="bg-[#0b1326] text-white">
        <div class="min-h-screen flex flex-col items-center justify-center px-4">
            <div class="w-full max-w-4xl bg-[#171f33] rounded-xl shadow-xl overflow-hidden">
                <div class="p-4 border-b border-gray-700 flex items-center justify-between">
                    <h2 class="text-lg font-bold tracking-wide">Camera: {stream_id}</h2>
                    <div class="flex items-center gap-3">
                        <span id="status" class="text-xs text-green-400 flex items-center gap-1">
                            <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                            LIVE
                        </span>
                        <button id="toggleBtn" class="bg-red-500 hover:bg-red-600 px-4 py-1 rounded text-sm font-semibold">
                            Disconnect
                        </button>
                    </div>
                </div>
                <div class="flex items-center justify-center bg-black">
                    <img id="video" class="w-full max-h-[70vh] object-contain"/>
                </div>
            </div>
        </div>

        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
        <script>
        let connected = true;
        const socket = io();

        socket.emit("stream", {{ stream_id: "{stream_id}" }});

        socket.on("frame", (data) => {{
            if (!connected) return;
            const blob = new Blob([data], {{ type: "image/jpeg" }});
            document.getElementById("video").src = URL.createObjectURL(blob);
        }});

        const btn = document.getElementById("toggleBtn");
        const status = document.getElementById("status");

        btn.addEventListener("click", () => {{
            if (connected) {{
                socket.disconnect();
                connected = false;
                btn.innerText = "Connect";
                btn.classList.remove("bg-red-500", "hover:bg-red-600");
                btn.classList.add("bg-green-500", "hover:bg-green-600");
                status.innerHTML = `<span class="w-2 h-2 bg-red-400 rounded-full"></span> DISCONNECTED`;
                status.classList.remove("text-green-400");
                status.classList.add("text-red-400");
            }} else {{
                socket.connect();
                socket.emit("stream", {{ stream_id: "{stream_id}" }});
                connected = true;
                btn.innerText = "Disconnect";
                btn.classList.remove("bg-green-500", "hover:bg-green-600");
                btn.classList.add("bg-red-500", "hover:bg-red-600");
                status.innerHTML = `<span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span> LIVE`;
                status.classList.remove("text-red-400");
                status.classList.add("text-green-400");
            }}
        }});
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)