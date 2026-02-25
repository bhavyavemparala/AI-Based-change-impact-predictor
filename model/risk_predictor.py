import pandas as pd

data = pd.read_csv("../data/sample_changes.csv")

def predict_risk(change_type):

    filtered = data[data["change_type"] == change_type]

    if len(filtered) == 0:

        return "Low"

    incident_rate = filtered["incident"].value_counts().get("yes", 0) / len(filtered)

    if incident_rate > 0.6:

        return "High"

    elif incident_rate > 0.3:

        return "Medium"

    else:

        return "Low"

print(predict_risk("config"))
