from flask import Flask, jsonify, request
from flask_cors import CORS
import joblib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load ML model
model = joblib.load("parking_model.pkl")
reservations = []
expired_reservations = []
# store latest parking data from ESP32
parking_data = {
    "distance1": 0,
    "distance2": 0,
    "status1": "FREE",
    "status2": "FREE"
}
@app.route("/reserve", methods=["POST"])
def reserve_slot():

    data = request.json

    slot = int(data["slot"])
    start = data["start"]
    end = data["end"]

    # check double booking

    for r in reservations:

        if r["slot"] == slot and r["start"] == start:

            return {
                "message":"Slot already reserved for this time"
            },400

    reservation = {

        "slot": slot,
        "start": start,
        "end": end,
        "price": 20,
        "status": "ACTIVE"

    }

    reservations.append(reservation)

    return {"message":"Reservation successful"}

def remove_expired_reservations():

    global reservations
    global expired_reservations

    now = datetime.now().strftime("%H:%M")

    active = []

    for r in reservations:

        if r["end"] <= now:

            r["status"] = "EXPIRED"

            expired_reservations.append(
                f"Reservation for Slot {r['slot']} expired"
            )

        else:

            active.append(r)

    reservations = active

@app.route("/expired")
def get_expired():

    global expired_reservations

    messages = expired_reservations

    expired_reservations = []

    return jsonify(messages)

@app.route("/reservations")
def get_reservations():

    remove_expired_reservations()

    return jsonify(reservations)

# ESP32 sends data here
@app.route("/update", methods=["POST"])
def update_data():
    global parking_data
    parking_data = request.json
    return {"message": "data updated"}

# dashboard reads parking data
@app.route("/data")
def get_data():
    return jsonify(parking_data)
parking_data = {
    "distance1": 0,
    "distance2": 0,
    "status1": "FREE",
    "status2": "FREE"
}


# prediction API
@app.route("/prediction")
def get_prediction():

    now = datetime.now()
    hour = now.hour
    day = now.weekday()

    prediction = model.predict([[hour, day]])

    capacity = 100
    free_spaces = capacity - int(prediction[0])

    return jsonify({
        "predicted_occupancy": int(prediction[0]),
        "predicted_free_spaces": free_spaces
    })

if __name__ == "__main__":
    app.run()