import pandas as pd
import requests

from datafog import PresidioEngine as presidio

url = "https://gist.githubusercontent.com/sidmohan0/757185e0b9ff63fe00096baa0ce3fa45/raw/0bef1789c1167acd286902f3466e54e151feaab3/sample.json"
response = requests.get(url)
data = response.json()
df = pd.DataFrame(data)
print(df.head())


# create a dataframe with some text data
def datafog_scanner(text):
    # create regex recognizer to scan for deal numbers
    regex_pattern = r"\$\S+"
    deal_regex = presidio.create_ad_hoc_regex_recognizer(
        regex_pattern=regex_pattern, entity_type="deal_values", score=0.4
    )

    return presidio.scan(
        text,
        deny_list=["Cisco", "Splunk", "CSCO", "SPLK"],
        ad_hoc_recognizers=[deal_regex],
    )


df["scan_results"] = df["text"].apply(datafog_scanner)
