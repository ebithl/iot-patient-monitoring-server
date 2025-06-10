#def generate_prompt(data):
#    vitals = data.get("vitals", {})
#    history = data.get("history", {})
#
#    patient_id = data.get("id", "Unknown")
#    name = data.get("name", "Unknown")
#    age = history.get("age", "N/A")
#    conditions = ', '.join(history.get("conditions", []))
#    medications = ', '.join(history.get("medications", []))
#
#    prompt = (
#        f"You are an AI clinical assistant.\n\n"
#        f"Patient details:\n"
#        f"ID: {patient_id}\n"
#        f"Name: {name}\n"
#        f"Age: {age}\n"
#        f"Conditions: {conditions or 'None'}\n"
#        f"Medications: {medications or 'None'}\n\n"
#        f"Current vitals:\n"
#        f"Heart Rate: {vitals.get('HR', 'N/A')} bpm\n"
#        f"SpO2: {vitals.get('SpO2', 'N/A')}%\n"
#        f"Respiratory Rate: {vitals.get('RR', 'N/A')} breaths/min\n"
#        f"Blood Pressure: {vitals.get('BP', 'N/A')}\n\n"
#        f"Based on this information, assess the patient condition in plain English. "
#        f"Highlight any concerning trends or vitals that require urgent attention."
#    )
#
#    return prompt
#

def generate_prompt(patient):
    name = patient.get("name", "Unknown")
    age = patient.get("age", "Unknown")
    conditions = ", ".join(patient.get("history", {}).get("conditions", [])) or "None"
    medications = ", ".join(patient.get("history", {}).get("medications", [])) or "None"

    vitals = patient.get("vitals", {})
    hr = vitals.get("HR", "N/A")
    spo2 = vitals.get("SpO2", "N/A")
    rr = vitals.get("RR", "N/A")
    bp = vitals.get("BP", "N/A")
    temp = vitals.get("Temp", "N/A")

    prompt = f"""
You are an experienced Clinical Decision Support Assistant. Your job is to strictly follow the format and provide a structured, professional assessment for the nurse/doctor based on the patient data below.

Do not include any text outside the sections provided. If data is missing, clearly indicate it as 'Not Available'.

---
**Patient Name**: {name}  
**Age**: {age}  
**Medical Conditions**: {conditions}  
**Medications**: {medications}  

**Vitals**:
- Heart Rate (HR): {hr} bpm
- SpO₂: {spo2}%
- Respiratory Rate (RR): {rr} bpm
- Blood Pressure (BP): {bp}
- Body Temperature (Temp): {temp}°F

---

🔍 **Clinical Interpretation**  
(Provide a concise paragraph interpreting the vitals and how they relate to medical history.)

🚨 **Red Flags**  
(List any abnormal or concerning findings from the vitals.)

🩺 **Suggested Immediate Actions**  
(Include actions such as monitoring, alerting physician, oxygen support, etc.)

📋 **Recommended Checks**  
(Suggest what further questions, tests, or follow-ups might be needed.)

"""
    return prompt.strip()


def generate_global_prompt(patients, messages):
    """
    Generate a system prompt to help LLM reason over global patient data.

    Parameters:
    - patients: list of patient dicts (each containing id, name, vitals, history)
    - messages: user-AI chat history

    Returns:
    - system prompt string
    """

    patient_lines = []
    for p in patients:
        vitals = p.get("vitals", {})
        patient_lines.append(
            f"{p['name']} (ID: {p['id']}): "
            f"HR={vitals.get('HR', 'N/A')}, "
            f"SpO₂={vitals.get('SpO2', 'N/A')}%, "
            f"RR={vitals.get('RR', 'N/A')} bpm, "
            f"BP={vitals.get('BP', 'N/A')}, "
            f"Temp={vitals.get('Temp', 'N/A')}"
        )
#        patient_lines.append(
#            f"{p['name']} (ID: {p['id']}): HR={vitals.get('HR', 'N/A')}, SpO₂={vitals.get('SpO2', 'N/A')}%, RR={vitals.get('RR', 'N/A')} bpm, BP={vitals.get('BP', 'N/A')}",
#            f"Temp={vitals.get('Temp', 'N/A')}"
#        )
    system_prompt = (
        "You are a clinical assistant with access to all current patient data. "
        "Analyze hospital-wide conditions to answer user questions about patient risk levels, admission/discharge trends, and general observations. "
        "Focus on summarizing patient severity and identifying any abnormalities or urgent cases. Use medical knowledge when reasoning about vitals.\n\n"
        "=== Current Patient Overview ===\n"
        + "\n".join(patient_lines) +
        "\n\nYou can use this data to answer queries such as:\n"
        "- Who is most critical?\n"
        "- Any abnormal trends?\n"
        "- How many patients admitted today?\n"
        "- Any red flags in patient health?\n"
        "- General vitals trend today?\n"
    )

    history = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

    return f"{system_prompt}\n\n=== Conversation ===\n{history}\nassistant:"
