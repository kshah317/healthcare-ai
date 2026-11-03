# notes.py
#
# twenty short, completely made-up clinical notes. none of these people exist. each note comes
# with a plain list of the facts that are in it (age, conditions, medications, allergies, lab
# values, and things that were ruled out), so the evaluation always knows what the right answer
# looks like. there is also a helper that writes a "gold" summary straight from those facts,
# which is a summary known to be faithful to its note.

NOTES = [
    {
        "id": "n01",
        "text": (
            "64 year old man seen for diabetes follow up. History of type 2 diabetes and "
            "hypertension. Current medications: metformin 500 mg twice daily and lisinopril "
            "10 mg daily. Allergic to penicillin. HbA1c today was 8.2 %. Blood pressure 138/86. "
            "No history of asthma. Plan: continue current medications and recheck HbA1c in 3 months."
        ),
        "age": 64, "sex": "M",
        "conditions": ["type 2 diabetes", "hypertension"],
        "meds": [("metformin", "500 mg"), ("lisinopril", "10 mg")],
        "allergies": ["penicillin"],
        "labs": [("HbA1c", "8.2", "%"), ("blood pressure", "138/86", "")],
        "negated": ["asthma"],
    },
    {
        "id": "n02",
        "text": (
            "58 year old woman here for a routine visit. She has high blood pressure and high "
            "cholesterol. Takes amlodipine 5 mg daily and atorvastatin 20 mg nightly. No known "
            "drug allergies. LDL was 142 mg/dL. Blood pressure 132/80. Discussed diet and exercise."
        ),
        "age": 58, "sex": "F",
        "conditions": ["hypertension", "hyperlipidemia"],
        "meds": [("amlodipine", "5 mg"), ("atorvastatin", "20 mg")],
        "allergies": [],
        "labs": [("LDL", "142", "mg/dL"), ("blood pressure", "132/80", "")],
        "negated": [],
    },
    {
        "id": "n03",
        "text": (
            "71 year old man with COPD and atrial fibrillation presents with increased cough. "
            "Medications include tiotropium 18 mcg daily, apixaban 5 mg twice daily and "
            "metoprolol 25 mg twice daily. Allergic to sulfa. Oxygen saturation 92 % on room air. "
            "Denies heart failure symptoms. Chest exam shows wheezing."
        ),
        "age": 71, "sex": "M",
        "conditions": ["copd", "atrial fibrillation"],
        "meds": [("tiotropium", "18 mcg"), ("apixaban", "5 mg"), ("metoprolol", "25 mg")],
        "allergies": ["sulfa"],
        "labs": [("oxygen saturation", "92", "%")],
        "negated": ["heart failure"],
    },
    {
        "id": "n04",
        "text": (
            "45 year old woman with asthma and migraine. Uses albuterol 90 mcg as needed and "
            "sumatriptan 50 mg at migraine onset. Allergic to latex. Pulse 78 bpm. No history of "
            "hypertension. Reviewed inhaler technique."
        ),
        "age": 45, "sex": "F",
        "conditions": ["asthma", "migraine"],
        "meds": [("albuterol", "90 mcg"), ("sumatriptan", "50 mg")],
        "allergies": ["latex"],
        "labs": [("pulse", "78", "bpm")],
        "negated": ["hypertension"],
    },
    {
        "id": "n05",
        "text": (
            "67 year old man with coronary artery disease and high cholesterol. Takes aspirin "
            "81 mg daily, rosuvastatin 40 mg daily and metoprolol 50 mg twice daily. No known "
            "allergies. LDL was 88 mg/dL. No history of diabetes. Counseled on walking program."
        ),
        "age": 67, "sex": "M",
        "conditions": ["coronary artery disease", "hyperlipidemia"],
        "meds": [("aspirin", "81 mg"), ("rosuvastatin", "40 mg"), ("metoprolol", "50 mg")],
        "allergies": [],
        "labs": [("LDL", "88", "mg/dL")],
        "negated": ["diabetes"],
    },
    {
        "id": "n06",
        "text": (
            "52 year old man with gout and obesity comes in with a painful left toe. Takes "
            "allopurinol 300 mg daily and ibuprofen 400 mg as needed. Allergic to shellfish. "
            "Uric acid 9.1 mg/dL. BMI 33. Advised to cut back on alcohol."
        ),
        "age": 52, "sex": "M",
        "conditions": ["gout", "obesity"],
        "meds": [("allopurinol", "300 mg"), ("ibuprofen", "400 mg")],
        "allergies": ["shellfish"],
        "labs": [("uric acid", "9.1", "mg/dL"), ("BMI", "33", "")],
        "negated": [],
    },
    {
        "id": "n07",
        "text": (
            "73 year old woman with heart failure and chronic kidney disease. Medications are "
            "furosemide 40 mg daily, spironolactone 25 mg daily and carvedilol 6.25 mg twice daily. "
            "Allergic to iodine. Creatinine 1.9 mg/dL and potassium 4.8 mmol/L. No evidence of "
            "atrial fibrillation on the tracing. Weight is stable."
        ),
        "age": 73, "sex": "F",
        "conditions": ["heart failure", "chronic kidney disease"],
        "meds": [("furosemide", "40 mg"), ("spironolactone", "25 mg"), ("carvedilol", "6.25 mg")],
        "allergies": ["iodine"],
        "labs": [("creatinine", "1.9", "mg/dL"), ("potassium", "4.8", "mmol/L")],
        "negated": ["atrial fibrillation"],
    },
    {
        "id": "n08",
        "text": (
            "34 year old woman with depression and anxiety. Takes sertraline 100 mg daily. No known "
            "drug allergies. Heart rate 88 bpm. Mood is improved since the last visit. Follow up "
            "in 6 weeks."
        ),
        "age": 34, "sex": "F",
        "conditions": ["depression", "anxiety"],
        "meds": [("sertraline", "100 mg")],
        "allergies": [],
        "labs": [("heart rate", "88", "bpm")],
        "negated": [],
    },
    {
        "id": "n09",
        "text": (
            "29 year old man with asthma. Uses fluticasone 110 mcg twice daily, albuterol 90 mcg as "
            "needed and montelukast 10 mg nightly. Allergic to peanuts. No history of pneumonia. "
            "Breathing is well controlled."
        ),
        "age": 29, "sex": "M",
        "conditions": ["asthma"],
        "meds": [("fluticasone", "110 mcg"), ("albuterol", "90 mcg"), ("montelukast", "10 mg")],
        "allergies": ["peanuts"],
        "labs": [],
        "negated": ["pneumonia"],
    },
    {
        "id": "n10",
        "text": (
            "61 year old woman with rheumatoid arthritis and hypothyroidism. Takes methotrexate "
            "15 mg weekly, levothyroxine 75 mcg daily and prednisone 5 mg daily. No known drug "
            "allergies. TSH 2.4. Joint pain is better this month."
        ),
        "age": 61, "sex": "F",
        "conditions": ["rheumatoid arthritis", "hypothyroidism"],
        "meds": [("methotrexate", "15 mg"), ("levothyroxine", "75 mcg"), ("prednisone", "5 mg")],
        "allergies": [],
        "labs": [("TSH", "2.4", "")],
        "negated": [],
    },
    {
        "id": "n11",
        "text": (
            "80 year old man with a history of stroke, atrial fibrillation and hypertension. "
            "Medications: warfarin 3 mg daily, lisinopril 20 mg daily and amlodipine 10 mg daily. "
            "Allergic to codeine. INR 2.4. Blood pressure 128/74. Warfarin dose unchanged."
        ),
        "age": 80, "sex": "M",
        "conditions": ["stroke", "atrial fibrillation", "hypertension"],
        "meds": [("warfarin", "3 mg"), ("lisinopril", "20 mg"), ("amlodipine", "10 mg")],
        "allergies": ["codeine"],
        "labs": [("INR", "2.4", ""), ("blood pressure", "128/74", "")],
        "negated": [],
    },
    {
        "id": "n12",
        "text": (
            "39 year old woman with a urinary tract infection and burning with urination. Started "
            "nitrofurantoin 100 mg twice daily. Allergic to sulfa. Temperature 37.8. No evidence "
            "of pneumonia. Told to drink plenty of fluids."
        ),
        "age": 39, "sex": "F",
        "conditions": ["urinary tract infection"],
        "meds": [("nitrofurantoin", "100 mg")],
        "allergies": ["sulfa"],
        "labs": [("temperature", "37.8", "")],
        "negated": ["pneumonia"],
    },
    {
        "id": "n13",
        "text": (
            "55 year old man with type 2 diabetes, chronic kidney disease and high blood pressure. "
            "Takes empagliflozin 10 mg daily, losartan 50 mg daily and metformin 1000 mg twice "
            "daily. No known allergies. HbA1c 7.4 % and eGFR 48. No history of stroke. Continue "
            "current plan."
        ),
        "age": 55, "sex": "M",
        "conditions": ["type 2 diabetes", "chronic kidney disease", "hypertension"],
        "meds": [("empagliflozin", "10 mg"), ("losartan", "50 mg"), ("metformin", "1000 mg")],
        "allergies": [],
        "labs": [("HbA1c", "7.4", "%"), ("eGFR", "48", "")],
        "negated": ["stroke"],
    },
    {
        "id": "n14",
        "text": (
            "48 year old woman with migraine and depression. Takes topiramate 50 mg twice daily and "
            "escitalopram 10 mg daily. No known drug allergies. Heart rate 72 bpm. Headaches are "
            "less frequent."
        ),
        "age": 48, "sex": "F",
        "conditions": ["migraine", "depression"],
        "meds": [("topiramate", "50 mg"), ("escitalopram", "10 mg")],
        "allergies": [],
        "labs": [("heart rate", "72", "bpm")],
        "negated": [],
    },
    {
        "id": "n15",
        "text": (
            "66 year old man with COPD and obstructive sleep apnea. Uses tiotropium 18 mcg daily, "
            "albuterol 90 mcg as needed and prednisone 20 mg for a flare. No known allergies. "
            "Oxygen saturation 90 %. Denies heart failure. Pulmonary rehab arranged."
        ),
        "age": 66, "sex": "M",
        "conditions": ["copd", "sleep apnea"],
        "meds": [("tiotropium", "18 mcg"), ("albuterol", "90 mcg"), ("prednisone", "20 mg")],
        "allergies": [],
        "labs": [("oxygen saturation", "90", "%")],
        "negated": ["heart failure"],
    },
    {
        "id": "n16",
        "text": (
            "42 year old woman with hypothyroidism. Takes levothyroxine 100 mcg daily. Allergic to "
            "amoxicillin. TSH 6.8. No evidence of anemia. Dose will be adjusted and labs repeated."
        ),
        "age": 42, "sex": "F",
        "conditions": ["hypothyroidism"],
        "meds": [("levothyroxine", "100 mcg")],
        "allergies": ["amoxicillin"],
        "labs": [("TSH", "6.8", "")],
        "negated": ["anemia"],
    },
    {
        "id": "n17",
        "text": (
            "77 year old man with heart failure, atrial fibrillation and type 2 diabetes. "
            "Medications: furosemide 20 mg daily, apixaban 2.5 mg twice daily, digoxin 0.125 mg "
            "daily and sitagliptin 50 mg daily. Allergic to penicillin. Potassium 4.2 mmol/L and "
            "HbA1c 7.9 %. No history of COPD. Fluid restriction reviewed."
        ),
        "age": 77, "sex": "M",
        "conditions": ["heart failure", "atrial fibrillation", "type 2 diabetes"],
        "meds": [("furosemide", "20 mg"), ("apixaban", "2.5 mg"), ("digoxin", "0.125 mg"), ("sitagliptin", "50 mg")],
        "allergies": ["penicillin"],
        "labs": [("potassium", "4.2", "mmol/L"), ("HbA1c", "7.9", "%")],
        "negated": ["copd"],
    },
    {
        "id": "n18",
        "text": (
            "31 year old woman with epilepsy. Takes lamotrigine 200 mg twice daily and levetiracetam "
            "500 mg twice daily. No known drug allergies. No history of stroke. No seizures in the "
            "past year."
        ),
        "age": 31, "sex": "F",
        "conditions": ["epilepsy"],
        "meds": [("lamotrigine", "200 mg"), ("levetiracetam", "500 mg")],
        "allergies": [],
        "labs": [],
        "negated": ["stroke"],
    },
    {
        "id": "n19",
        "text": (
            "59 year old man with acid reflux, hypertension and obesity. Takes omeprazole 20 mg "
            "daily, losartan 100 mg daily and hydrochlorothiazide 25 mg daily. Allergic to shellfish. "
            "BMI 31. Blood pressure 144/92. No history of type 2 diabetes. Weight loss advised."
        ),
        "age": 59, "sex": "M",
        "conditions": ["gerd", "hypertension", "obesity"],
        "meds": [("omeprazole", "20 mg"), ("losartan", "100 mg"), ("hydrochlorothiazide", "25 mg")],
        "allergies": ["shellfish"],
        "labs": [("BMI", "31", ""), ("blood pressure", "144/92", "")],
        "negated": ["type 2 diabetes"],
    },
    {
        "id": "n20",
        "text": (
            "69 year old woman with osteoarthritis and hypertension. Takes naproxen 500 mg twice "
            "daily, amlodipine 5 mg daily and acetaminophen 500 mg as needed. Allergic to sulfa. "
            "Blood pressure 130/78. No history of gout. Knee exercises reviewed."
        ),
        "age": 69, "sex": "F",
        "conditions": ["osteoarthritis", "hypertension"],
        "meds": [("naproxen", "500 mg"), ("amlodipine", "5 mg"), ("acetaminophen", "500 mg")],
        "allergies": ["sulfa"],
        "labs": [("blood pressure", "130/78", "")],
        "negated": ["gout"],
    },
]


def gold_summary(note):
    # builds a summary straight from the note's facts, so it is faithful by construction
    who = "man" if note["sex"] == "M" else "woman"
    parts = [f"{note['age']} year old {who} with {', '.join(note['conditions'])}."]

    # only mention medications, allergies and labs when the note has some
    if note["meds"]:
        parts.append("Takes " + ", ".join(f"{d} {dose}" for d, dose in note["meds"]) + ".")
    if note["allergies"]:
        parts.append("Allergic to " + ", ".join(note["allergies"]) + ".")
    if note["labs"]:
        labs = ", ".join(f"{n} {v} {u}".strip() for n, v, u in note["labs"])
        parts.append(f"Results: {labs}.")
    return " ".join(parts)
