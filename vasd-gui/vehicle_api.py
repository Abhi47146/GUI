from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import base64
import os
import uuid
from fastapi.staticfiles import StaticFiles
from configparser import ConfigParser
from fastapi import Query

conf = ConfigParser()
conf.read('config.ini')
min_speed = int(conf.get("speed", "min_speed"))
max_speed = int(conf.get("speed", "max_speed"))
class_names = dict(conf.items("class"))
class_names = {int(k): v for k, v in class_names.items()}

app = FastAPI()

IMAGE_FOLDER = "static/images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

data_store = []  


class VehicleEvent(BaseModel):
    scn: str
    lane: int
    speed: int
    vehicle_class: int
    vehicle_image: str
    timestamp: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/vehicle")
async def vehicle_entry(event: VehicleEvent):

    image_url = ""

    if event.vehicle_image:
        img_name = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(IMAGE_FOLDER, img_name)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(event.vehicle_image))

        # URL for frontend
        image_url = f"/static/images/{img_name}"

    vehicle_class_name = class_names.get(event.vehicle_class, "Unknown")
    entry = {
        "timestamp": event.timestamp,
        "name": event.scn,
        "lane": event.lane,
        "speed": event.speed,
        "min_speed": min_speed,
        "max_speed": max_speed,
        "vehicle_class": vehicle_class_name,
        "violation": "Over Speed" if event.speed > max_speed else "Normal",
        "image": image_url,  
        "created_at": datetime.now()
    }

    data_store.append(entry)

    return {"status": "success"}


@app.get("/api/data")
async def get_data(
    from_time: str = Query(None, alias="from"),
    to_time: str = Query(None, alias="to"),
    vehicle_class: str = None,
    name: str = None
):
    global data_store

    now = datetime.now()

    # keep last 7 days
    filtered = [
        d for d in data_store
        if now - d["created_at"] <= timedelta(days=7)
    ]

    # filter by time
    if from_time and to_time:
        from_dt = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S")
        to_dt = datetime.strptime(to_time, "%Y-%m-%d %H:%M:%S")

        filtered = [
            d for d in filtered
            if from_dt <= datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") <= to_dt
        ]

    # filter by vehicle class
    if vehicle_class:
        filtered = [
            d for d in filtered
            if d["vehicle_class"] == vehicle_class
        ]

    # filter by name (SCN)
    if name:
        filtered = [
            d for d in filtered
            if name.lower() in d["name"].lower()
        ]

    return filtered

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
