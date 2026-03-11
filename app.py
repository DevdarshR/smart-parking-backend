from flask import Flask, jsonify, request
from flask_cors import CORS
import joblib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load ML model
model = joblib.load("parking_model.pkl")
reservations = []
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

    reservation = {
        "slot": data["slot"],
        "start": data["start"],
        "end": data["end"],
        "price": data["price"]
    }

    reservations.append(reservation)

    return {"message":"slot reserved"}

def remove_expired_reservations():

    now = datetime.now().strftime("%H:%M")

    global reservations

    reservations = [
        r for r in reservations
        if r["end"] > now
    ]

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

@app.route("/update", methods=["POST"])
def update_data():
    global parking_data
    parking_data = request.json
    return {"message": "updated"}

@app.route("/data")
def get_data():
    return jsonify(parking_data)

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