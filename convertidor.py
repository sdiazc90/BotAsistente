import json

with open("credentials.json", "r") as f:
    data = json.load(f)
    print(json.dumps(data))
