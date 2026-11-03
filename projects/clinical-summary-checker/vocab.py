# vocab.py
#
# the word lists the checker leans on. the checker needs to know what a drug name, a
# condition, or a "this is ruled out" phrase looks like, and this file is where that
# knowledge lives. it is deliberately small and plain so anyone can read it and add to it.

import re

# common medication names (generic names, lowercase)
DRUGS = {
    "metformin", "lisinopril", "amlodipine", "atorvastatin", "simvastatin", "rosuvastatin",
    "metoprolol", "carvedilol", "losartan", "hydrochlorothiazide", "furosemide",
    "spironolactone", "insulin", "warfarin", "apixaban", "clopidogrel", "aspirin",
    "omeprazole", "pantoprazole", "levothyroxine", "albuterol", "fluticasone", "tiotropium",
    "montelukast", "prednisone", "sertraline", "citalopram", "escitalopram", "gabapentin",
    "ibuprofen", "naproxen", "acetaminophen", "amoxicillin", "azithromycin",
    "ciprofloxacin", "doxycycline", "nitrofurantoin", "sitagliptin", "glipizide",
    "empagliflozin", "liraglutide", "tamsulosin", "lorazepam", "tramadol", "oxycodone",
    "digoxin", "diltiazem", "cetirizine", "loratadine", "allopurinol", "methotrexate",
    "hydroxychloroquine", "lamotrigine", "levetiracetam", "topiramate", "sumatriptan",
}

# word endings that usually mean "this is a drug", used to catch drugs that are not in the
# list above. a word has to be at least 7 letters long so short everyday words are left alone.
DRUG_SUFFIXES = (
    "pril", "sartan", "statin", "olol", "formin", "azole", "cillin", "mycin", "floxacin",
    "dipine", "zepam", "prazole", "tidine", "gliptin", "gliflozin", "glutide", "parin",
    "xaban", "mab", "triptan", "setron", "oxetine", "triptyline",
)

# conditions: the standard name on the left, the different ways people write it on the right
CONDITIONS = {
    "type 2 diabetes": ["type 2 diabetes mellitus", "type 2 diabetes", "type ii diabetes", "t2dm"],
    "type 1 diabetes": ["type 1 diabetes mellitus", "type 1 diabetes", "type i diabetes", "t1dm"],
    "diabetes": ["diabetes mellitus", "diabetes"],
    "hypertension": ["hypertension", "high blood pressure", "htn"],
    "hyperlipidemia": ["hyperlipidemia", "high cholesterol", "dyslipidemia"],
    "asthma": ["asthma"],
    "copd": ["chronic obstructive pulmonary disease", "copd"],
    "heart failure": ["congestive heart failure", "heart failure", "chf"],
    "atrial fibrillation": ["atrial fibrillation", "afib", "a-fib"],
    "coronary artery disease": ["coronary artery disease", "cad"],
    "chronic kidney disease": ["chronic kidney disease", "ckd"],
    "hypothyroidism": ["hypothyroidism"],
    "depression": ["depression"],
    "anxiety": ["anxiety"],
    "migraine": ["migraine"],
    "osteoarthritis": ["osteoarthritis"],
    "rheumatoid arthritis": ["rheumatoid arthritis"],
    "pneumonia": ["pneumonia"],
    "urinary tract infection": ["urinary tract infection", "uti"],
    "gout": ["gout"],
    "obesity": ["obesity"],
    "anemia": ["anemia"],
    "stroke": ["stroke"],
    "epilepsy": ["epilepsy"],
    "sleep apnea": ["obstructive sleep apnea", "sleep apnea", "osa"],
    "gerd": ["gastroesophageal reflux", "acid reflux", "gerd"],
    "pulmonary embolism": ["pulmonary embolism"],
    "myocardial infarction": ["myocardial infarction", "heart attack"],
    "cirrhosis": ["cirrhosis"],
    "psoriasis": ["psoriasis"],
    "cellulitis": ["cellulitis"],
}

# a general word that stands in for several specific ones: saying "diabetes" is fine if the
# note says type 1 or type 2
PARENTS = {"diabetes": ["type 2 diabetes", "type 1 diabetes"]}

# phrases that mean the thing right after them is NOT happening to the patient
NEGATION_CUES = re.compile(
    r"\b(no|denies|denied|without|negative for|ruled out|no history of|no evidence of|"
    r"free of|never had|not)\b"
)

# phrases that mean the thing is about someone else, like a relative
OTHER_PERSON_CUES = re.compile(r"\b(family history of|mother had|father had|brother had|sister had)\b")

# lab and vital names, used to spot "<name> <number>" claims
LAB_NAMES = [
    "hba1c", "a1c", "ldl", "hdl", "creatinine", "egfr", "glucose", "potassium", "sodium",
    "hemoglobin", "bmi", "heart rate", "pulse", "temperature", "oxygen saturation", "spo2",
    "inr", "tsh", "uric acid", "blood pressure",
]
