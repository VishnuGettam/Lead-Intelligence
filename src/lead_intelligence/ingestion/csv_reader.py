import pandas as pd 

# Read the data 

def read_leads(file_path:str)->pd.DataFrame:

    leads = pd.read_csv(file_path)
    return leads
