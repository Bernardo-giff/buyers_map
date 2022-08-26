from simple_salesforce import Salesforce
import pandas as pd

with open('salesforce_login.txt') as f:
    username, password, token = [x.strip("\n") for x in f.readlines()]
sf = Salesforce(username=username, password=password, security_token=token)
sf = Salesforce(username=username, password=password, security_token=token)

def get_salesforce_table(query_file):
    """Function to get the query from the queries file and return the salesforce df"""
    with open(query_file) as f:
        contents = f.readlines()
    query = ''.join(contents).replace('\n', '')
    df = sf.query_all(query)
    df = pd.DataFrame(df['records']).drop(columns='attributes')
    return df
