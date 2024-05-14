import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from datafog import PresidioEngine as presidio


def scan_line(line):
    return str(presidio.scan(line))


with open("sotu_2023.txt", "r") as f:
    lines = f.readlines()
    lines = [line.strip() for line in lines]
    lines = lines[0:20]
    df = pd.DataFrame(lines)
    df = df.to_dict(orient="list")
    scan_output = []
    print(len(df))

# Using ThreadPoolExecutor to parallelize the scanning process
with ThreadPoolExecutor() as executor:
    scan_output = list(executor.map(scan_line, df[0]))

print(scan_output)
with open("scan_output.json", "w") as f:
    json.dump(scan_output, f)
