from flask import Flask, jsonify, request
from flask_cors import CORS
import joblib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load ML model 
# (Added a try-except block so your server doesn't crash if the model file is missing during testing)
try:
    model = joblib.load("parking_model.pkl")
except FileNotFoundError:
    model = None

reservations = []
expired_reservations = []

# store latest parking data from ESP32
parking_data = {
    "distance1": 0,
    "distance2": 0,
    "status1": "FREE",
    "status2": "FREE"
}

# Helper function to convert "HH:MM" into total minutes for easy math
def time_to_mins(t_str):
    h, m = map(int, t_str.split(':'))
    return h * 60 + m

@app.route("/reserve", methods=["POST"])
def reserve_slot():
    data = request.json
    slot = int(data["slot"])
    start = data.get("start")
    end = data.get("end")
    
    calculated_price = data.get("price", 0) 
    pay_method = data.get("payment_method", "UPI")
    vehicle_no = data.get("vehicle_no", "UNKNOWN")
    booking_id = data.get("booking_id", "LX-00000")
    
    # NEW: Grab the username of the person booking
    username = data.get("username", "guest")

    new_start_mins = time_to_mins(start)
    new_end_mins = time_to_mins(end)

    # NEW: Strict Overlap Check
    for r in reservations:
        if r["slot"] == slot:
            ex_start = time_to_mins(r["start"])
            ex_end = time_to_mins(r["end"])
            
            # Logic: If New Start is before Existing End AND New End is after Existing Start -> OVERLAP!
            if new_start_mins < ex_end and new_end_mins > ex_start:
                return jsonify({"message": f"Slot {slot} is already booked during this time."}), 400

    reservation = {
        "username": username, # Save the owner
        "booking_id": booking_id, 
        "vehicle_no": vehicle_no, 
        "slot": slot,
        "start": start,
        "end": end,
        "price": calculated_price,
        "payment_method": pay_method,
        "status": "ACTIVE"
    }

    reservations.append(reservation)
    return jsonify({"message": "Reservation successful"}), 200
    
# --- NEW ENDPOINT: Manual Deletion ---
@app.route("/delete_reservation", methods=["POST"])
def delete_reservation():
    global reservations
    data = request.json
    
    # Filter out the reservation that matches the incoming slot and time
    reservations = [
        r for r in reservations 
        if not (r["slot"] == int(data.get("slot")) and r["start"] == data.get("start") and r["end"] == data.get("end"))
    ]
    
    return jsonify({"message": "Reservation deleted successfully"}), 200
# -------------------------------------


def remove_expired_reservations():
    global reservations
    global expired_reservations

    now = datetime.now().strftime("%H:%M")
    active = []

    for r in reservations:
        if r["end"] <= now:
            r["status"] = "EXPIRED"
            expired_reservations.append(f"Reservation for Slot {r['slot']} expired")
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
    return jsonify({"message": "data updated"})

# dashboard reads parking data
@app.route("/data")
def get_data():
    return jsonify(parking_data)


# prediction API
@app.route("/prediction")
def get_prediction():
    now = datetime.now()
    hour = now.hour
    day = now.weekday()

    if model:
        prediction = model.predict([[hour, day]])
        predicted_occupancy = int(prediction[0])
    else:
        # Fallback if model isn't loaded
        predicted_occupancy = 0

    capacity = 100
    free_spaces = capacity - predicted_occupancy

    return jsonify({
        "predicted_occupancy": predicted_occupancy,
        "predicted_free_spaces": free_spaces
    })

if __name__ == "__main__":
    # Added debug=True for easier troubleshooting during development
    app.run(debug=True)
