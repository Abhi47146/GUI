from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import base64
import os
import uuid
from fastapi.staticfiles import StaticFiles
from configparser import ConfigParser
from typing import Optional

# Load class names
conf = ConfigParser()
conf.read('config.ini')
class_names = dict(conf.items("class"))
class_names = {int(k): v for k, v in class_names.items()}

app = FastAPI()

# Folders
BASE_FOLDER = "static/images"
VEHICLE_FOLDER = os.path.join(BASE_FOLDER, "vehicles")
PLATE_FOLDER = os.path.join(BASE_FOLDER, "plates")

os.makedirs(VEHICLE_FOLDER, exist_ok=True)
os.makedirs(PLATE_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory store
data_store = []

# Model
class VehicleEvent(BaseModel):
    scn: str
    lane: int
    vehicle_image: str = ""
    plate_image: str = ""
    plate_no: str
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

    vehicle_url = ""
    plate_url = ""

    # Save vehicle image
    if event.vehicle_image:
        img_name = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(VEHICLE_FOLDER, img_name)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(event.vehicle_image))

        vehicle_url = f"/static/images/vehicles/{img_name}"

    # Save plate image
    if event.plate_image:
        img_name = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(PLATE_FOLDER, img_name)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(event.plate_image))

        plate_url = f"/static/images/plates/{img_name}"
       


    entry = {
        "timestamp": event.timestamp,
        "scn": event.scn,
        "lane": event.lane,
        "vehicle_image": vehicle_url,
        "plate_image": plate_url,
        "plate_no": event.plate_no,
        "created_at": datetime.now()
    }

    data_store.append(entry)

    return {"status": "success"}

@app.get("/api/data")
def get_data(
    stream_id: Optional[str] = None,
    lane: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    plate_no: Optional[str] = None
):

    data = data_store.copy()

    # Filter by plate number
    if plate_no:
        search = plate_no.replace(" ", "").replace("-", "").lower()

        data = [
            d for d in data
            if d.get("plate_no") and
            search in d["plate_no"].replace(" ", "").replace("-", "").lower()
        ]

    # Filter by stream_id
    if stream_id:
        data = [d for d in data if d.get("scn") == stream_id]

    # Filter by lane
    if lane:
        data = [
            d for d in data
            if d.get("lane") and str(d["lane"]).lower() == lane.lower()
        ]

    # Filter by time
    if from_time and to_time:
        from_dt = datetime.strptime(from_time, "%d-%m-%Y %H:%M:%S")
        to_dt = datetime.strptime(to_time, "%d-%m-%Y %H:%M:%S")

        data = [d for d in data
            if from_dt <= datetime.strptime(d["timestamp"],"%d-%m-%Y %H:%M:%S") <= to_dt
        ]

    # Sort latest first
    data.sort(key=lambda x: datetime.strptime(x["timestamp"],"%d-%m-%Y %H:%M:%S"),reverse=True)

    return data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8070)