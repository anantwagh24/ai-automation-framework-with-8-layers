import csv
from collections import Counter
from aiauto.common.metrics import precision_recall_f1

def evaluate_predictions(csv_path: str):
    # expects CSV with columns: y_true,y_pred
    tp = fp = fn = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yt = row["y_true"].strip()
            yp = row["y_pred"].strip()
            if yp == "1" and yt == "1": tp += 1
            elif yp == "1" and yt != "1": fp += 1
            elif yp != "1" and yt == "1": fn += 1
    return precision_recall_f1(tp, fp, fn)
