import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import os
import sqlite3
import time
from typing import Optional
from configparser import ConfigParser
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

conf = ConfigParser()
conf.read('config.ini')
day = conf.getint("data_cleanup", "days")

DB_FILE = "vehicle_events.db"
BASE_IMAGE_DIR = "/var/i-phalakam/data/images"

os.makedirs(BASE_IMAGE_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            scn TEXT NOT NULL,
            lane INTEGER NOT NULL,
            vehicle_image TEXT,
            plate_image TEXT,
            plate_no TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON vehicle_events(timestamp)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scn
        ON vehicle_events(scn)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_plate_no
        ON vehicle_events(plate_no)
    """)

    conn.commit()
    conn.close()


def delete_old_data():
    conn = get_db()
    # Retain data for 2 days
    cutoff = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")

    rows = conn.execute(
        """
        SELECT id, vehicle_image, plate_image
        FROM vehicle_events
        WHERE created_at < ?
        """,
        (cutoff,),
    ).fetchall()

    deleted = 0

    for row in rows:
        # Delete vehicle image
        if row["vehicle_image"]:
            rel_path = row["vehicle_image"].replace("/static/images/", "", 1)
            file_path = os.path.join(BASE_IMAGE_DIR, rel_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                remove_empty_parents(os.path.dirname(file_path))

        # Delete plate image
        if row["plate_image"]:
            rel_path = row["plate_image"].replace("/static/images/", "", 1)
            file_path = os.path.join(BASE_IMAGE_DIR, rel_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                remove_empty_parents(os.path.dirname(file_path))

        deleted += 1

    conn.execute(
        """
        DELETE FROM vehicle_events
        WHERE created_at < ?
        """,
        (cutoff,),
    )

    conn.commit()
    conn.close()

    print(f"[CLEANUP] Deleted {deleted} records and associated files older than 2 days")


def remove_empty_parents(dir_path: str):
    """Recursively removes empty parent directories up to BASE_IMAGE_DIR."""
    try:
        while dir_path != BASE_IMAGE_DIR and os.path.exists(dir_path):
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                dir_path = os.path.dirname(dir_path)
            else:
                break
    except Exception as e:
        print(f"[CLEANUP DIR ERROR] {e}")


async def cleanup_task():
    while True:
        try:
            delete_old_data()
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")

        # Run cleanup every hour
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(cleanup_task())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

# Serves files under /var/i-phalakam/data/images via /static/images/
app.mount("/static/images", StaticFiles(directory=BASE_IMAGE_DIR), name="static_images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/vehicle")
async def vehicle_entry(
    scn: str = Form(...),
    lane: int = Form(...),
    plate_no: str = Form(...),
    timestamp: str = Form(...),
    vehicle_image: Optional[UploadFile] = File(None),
    plate_image: Optional[UploadFile] = File(None),
):
    total_start = time.perf_counter()

    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")

    # Path: /var/i-phalakam/data/images/YYYY/MM/DD/{scn}/
    relative_folder = os.path.join(year, month, day, scn)
    target_folder = os.path.join(BASE_IMAGE_DIR, relative_folder)
    os.makedirs(target_folder, exist_ok=True)

    vehicle_url = ""
    plate_url = ""
    total_bytes = 0

    decode_start = time.perf_counter()

    # Process Vehicle Image - will overwrite if img_{plate_no}.jpg already exists
    if vehicle_image:
        vehicle_bytes = await vehicle_image.read()
        total_bytes += len(vehicle_bytes)
        img_name = f"img_{plate_no}.jpg"

        file_path = os.path.join(target_folder, img_name)
        with open(file_path, "wb") as f:
            f.write(vehicle_bytes)

        vehicle_url = f"/static/images/{relative_folder}/{img_name}"

    # Process Plate Image - will overwrite if np_{plate_no}.jpg already exists
    if plate_image:
        plate_bytes = await plate_image.read()
        total_bytes += len(plate_bytes)
        img_name = f"np_{plate_no}.jpg"

        file_path = os.path.join(target_folder, img_name)
        with open(file_path, "wb") as f:
            f.write(plate_bytes)

        plate_url = f"/static/images/{relative_folder}/{img_name}"

    decode_end = time.perf_counter()

    db_start = time.perf_counter()

    conn = get_db()
    conn.execute(
        """
        INSERT INTO vehicle_events (
            timestamp,
            scn,
            lane,
            vehicle_image,
            plate_image,
            plate_no,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            scn,
            lane,
            vehicle_url,
            plate_url,
            plate_no,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    event_id_db = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    db_end = time.perf_counter()

    decode_ms = (decode_end - decode_start) * 1000
    db_ms = (db_end - db_start) * 1000
    total_ms = (db_end - total_start) * 1000

    print(
        f"Save: {decode_ms:.2f} ms | "
        f"DB Insert: {db_ms:.2f} ms | "
        f"Server Total: {total_ms:.2f} ms | "
        f"Payload: {total_bytes / 1024:.1f} KB"
    )

    return {
        "status": "success",
        "id": event_id_db,
        "server_time_ms": round(total_ms, 2),
    }

@app.get("/api/data")
def get_data(
    stream_id: Optional[str] = None,
    lane: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    plate_no: Optional[str] = None,
):
    conn = get_db()

    query = """
        SELECT
            id,
            timestamp,
            scn,
            lane,
            vehicle_image,
            plate_image,
            plate_no,
            created_at
        FROM vehicle_events
        WHERE 1=1
    """

    params = []

    if stream_id:
        query += " AND scn = ?"
        params.append(stream_id)

    if lane:
        query += " AND lane = ?"
        params.append(int(lane))

    if plate_no:
        search = plate_no.replace(" ", "").replace("-", "").lower()

        query += """
            AND REPLACE(
                REPLACE(LOWER(plate_no), ' ', ''),
                '-',
                ''
            ) LIKE ?
        """
        params.append(f"%{search}%")

    if from_time:
        query += " AND timestamp >= ?"
        params.append(from_time)

    if to_time:
        query += " AND timestamp <= ?"
        params.append(to_time)

    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070, log_level="warning")