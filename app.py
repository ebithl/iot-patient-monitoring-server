from flask import Flask, request, jsonify
#import openai
import os
import threading
import time
import random
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from prompts import generate_prompt, generate_global_prompt
import requests
from openai import OpenAI
from dotenv import load_dotenv
import os
from flask_cors import CORS
import pprint
from flask_socketio import SocketIO, emit


load_dotenv()  # This loads variables from .env into os.environ

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

#openai.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory patient store
patients = {
    f"P{str(i).zfill(3)}": {
        "id": f"P{str(i).zfill(3)}",
        "name": f"Patient {i}",
        "gender": random.choice(["M", "F"]),
        "age": random.randint(20, 90),
        "vitals": {},
        "risk": "low",
        "history": {
            "conditions": [],
            "medications": []
        }
    }
    for i in range(1, 41)
}

current_vitals = {}

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "patient/vitals"

@app.route("/patients", methods=["GET"])
def get_patients():
    #return jsonify(patients_data)
    return jsonify(list(patients.values()))

# --- LLM CDSA Endpoint ---
@app.route("/cdsa", methods=["POST"])
def cdsa():
    data = request.get_json()
    messages = data.get("messages", [])
    
    if "patients" in data:
        # Global Query Mode
        prompt = generate_global_prompt(data["patients"], messages)
    else:
        # Per-patient Mode
        prompt = generate_prompt(data.get("patient"))

    chat_history = [{"role": "system", "content": prompt}]
    for m in messages:
        chat_history.append({
            "role": "user" if m.get("sender", "") != "AI" else "assistant",
            "content": m.get("text", "")
        })

    completion = client.chat.completions.create(
        model="gpt-4",
        messages=chat_history
    )

    reply = completion.choices[0].message.content
    return jsonify({"message": reply})


# --- LLM Chat Interface Endpoint ---
@app.route("/chat", methods=["POST"])
def chat():
    query = request.json["query"]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}]
    )
    return jsonify({"answer": response.choices[0].message.content})


# MQTT simulator thread
def simulator_thread():
    publisher = mqtt.Client()
    publisher.connect(MQTT_BROKER, MQTT_PORT)
    while True:
        for pid in patients:
            #print("simulator_thread(): ", pid)
            #vitals = generate_vitals()
            vitals = generate_vitals(pid)
            message = {"id": pid, "vitals": vitals}
            publisher.publish(MQTT_TOPIC, json.dumps(message))
        time.sleep(5)
        
# --- Background Vital Simulator Thread ---
def simulate_vitals():
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)
    
    while True:
        for patient in patients:
            vitals = {
                "HR": random.randint(60, 100),
                "SpO2": random.randint(90, 100),
                "RR": random.randint(12, 20),
                "BP": f"{random.randint(100, 130)}/{random.randint(60, 90)}",
                "Temp": round(random.uniform(36.0, 38.5), 1)
            }
            topic = f"vitals/{patient['id']}"
            client.publish(topic, json.dumps(vitals))
        time.sleep(5)  # simulate every 5 seconds

# Generate random vitals
def generate_vitals():
    return {
        "HR": random.randint(60, 150),
        "SpO2": random.randint(85, 100),
        "RR": random.randint(12, 35),
        "BP": f"{random.randint(90, 160)}/{random.randint(60, 100)}",
        "Temp": round(random.uniform(97.0, 104.0), 1)
    }

def generate_vitals(pid):
    if pid not in current_vitals:
        # Initialize with normal baseline
        current_vitals[pid] = {
            "HR": random.randint(70, 90),
            "SpO2": random.randint(95, 98),
            "RR": random.randint(16, 20),
            "BP_sys": random.randint(110, 120),
            "BP_dia": random.randint(70, 80),
            "Temp": round(random.uniform(97.5, 98.5), 1)
        }

    vitals = current_vitals[pid]

    # Gradually adjust each vital within bounds
    def smooth_value(value, min_val, max_val, step=1):
        delta = random.choice([-step, 0, step])
        return max(min_val, min(max_val, value + delta))

    def smooth_float(value, min_val, max_val, step=0.1):
        delta = random.choice([-step, 0, step])
        return round(max(min_val, min(max_val, value + delta)), 1)

    vitals["HR"] = smooth_value(vitals["HR"], 60, 150, step=2)
    vitals["SpO2"] = smooth_value(vitals["SpO2"], 85, 100)
    vitals["RR"] = smooth_value(vitals["RR"], 12, 35)
    vitals["BP_sys"] = smooth_value(vitals["BP_sys"], 90, 160, step=2)
    vitals["BP_dia"] = smooth_value(vitals["BP_dia"], 60, 100, step=2)
    vitals["Temp"] = smooth_float(vitals["Temp"], 97.0, 104.0)

    return {
        "HR": vitals["HR"],
        "SpO2": vitals["SpO2"],
        "RR": vitals["RR"],
        "BP": f"{vitals['BP_sys']}/{vitals['BP_dia']}",
        "Temp": vitals["Temp"]
    }

    
    
# --- Background Simulator Thread ---
def simulate_patients():
    mqtt_client = mqtt.Client()
    mqtt_client.connect("localhost", 1883)
    topic = "patient/vitals"

    patients = [
        {
            "id": "P001",
            "name": "John Doe",
            "history": {
                "age": 72,
                "gender": 1,
                "conditions": ["COPD", "Hypertension"],
                "medications": ["Lisinopril", "Albuterol"]
            }
        },
        {
            "id": "P002",
            "name": "Jane Smith",
            "history": {
                "age": 58,
                "gender": 2,
                "conditions": ["Diabetes"],
                "medications": ["Metformin"]
            }
        }
    ]

    def generate_vitals():
        return {
            "HR": random.randint(60, 140),
            "SpO2": round(random.uniform(85, 99), 1),
            "RR": random.randint(12, 30),
            "BP": f"{random.randint(100, 160)}/{random.randint(60, 100)}"
        }

    while True:
        for patient in patients:
            payload = {
                "id": patient["id"],
                "name": patient["name"],
                "timestamp": datetime.utcnow().isoformat(),
                "history": patient["history"],
                "vitals": generate_vitals()
            }
            mqtt_client.publish(topic, json.dumps(payload))
            print(f"[Simulator] Published vitals for {patient['name']}")
        time.sleep(10)


# --- Background MQTT Listener Thread ---
def mqtt_listener():
    def on_message(client, userdata, msg):
        patient_data = json.loads(msg.payload.decode())
        try:
            print(f"[Listener] Received vitals for {patient_data['name']}")
            # Call the CDSA endpoint internally
            response = requests.post("http://localhost:5000/cdsa", json=patient_data)
            summary = response.json().get("summary", "No summary returned.")
            print(f"[CDSA] {patient_data['name']}: {summary}\n")
        except Exception as e:
            print(f"[Error] Failed to process message: {e}")

    client = mqtt.Client()
    client.connect("localhost", 1883)
    client.subscribe("patient/vitals")
    client.on_message = on_message
    client.loop_forever()

#patients = [
#    {
#        "id": "P001",
#        "name": "Alice Smith",
#        "age": 65,
#        "gender": "female",
#        "vitals": {
#            "HR": 82,
#            "SpO2": 97,
#            "RR": 16,
#            "BP": "120/80",
#            "Temp": "98"
#        },
#        "history": {
#            "conditions": ["Diabetes"],
#            "medications": ["Metformin"]
#        }
#    },
#    {
#        "id": "P002",
#        "name": "John Doe",
#        "age": 75,
#        "gender": "male",
#        "vitals": {
#            "HR": 90,
#            "SpO2": 95,
#            "RR": 22,
#            "BP": "140/100",
#            "Temp": "100"
#        },
#        "history": {
#            "conditions": ["Diabetes"],
#            "medications": ["Metformin"]
#        }
#    },    
#]

# MQTT subscriber callback
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    pid = payload.get("id")
    #print("payload:", payload)
    #print("Received MQTT message for patient ID:", pid)
    #print("Received MQTT message for patient ID:", pid.get("id"))
    #print("Current patients keys:", list(patients.keys()))
    #pidd = pid.get("id")

    vitals = payload.get("vitals")
    #print("vitals:", vitals)
    if pid in patients:   
        patients[pid]["vitals"] = vitals
        risk = evaluate_risk(vitals)
        patients[pid]["risk"] = risk
        socketio.emit("vitals_update", {"id": pid, "vitals": vitals, "risk": risk})

# Start MQTT subscriber thread
def subscriber_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()

def subscribe_vitals():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.subscribe("vitals/#")
    client.loop_forever()

# Dummy risk model
def evaluate_risk(vitals):
    hr = vitals.get("HR", 0)
    spo2 = vitals.get("SpO2", 100)
    rr = vitals.get("RR", 0)
    temp = vitals.get("Temp", 98.6)

    if hr > 120 or spo2 < 90 or rr > 30 or temp > 102:
        return "high"
    elif hr > 100 or spo2 < 95 or rr > 20 or temp > 100:
        return "medium"
    else:
        return "low"
        
        
# --- Start Flask + Threads ---
if __name__ == "__main__":
    threading.Thread(target=simulator_thread, daemon=True).start()
    threading.Thread(target=subscriber_thread, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)
    app.run(debug=True, use_reloader=False)
    
#if __name__ == "__main__":
#    threading.Thread(target=simulate_vitals, daemon=True).start()
#    threading.Thread(target=mqtt_listener, daemon=True).start()
##    threading.Thread(target=simulate_patients, daemon=True).start()
##    threading.Thread(target=mqtt_listener, daemon=True).start()
#    app.run(debug=True, use_reloader=False)
