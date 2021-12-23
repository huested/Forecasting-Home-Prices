# -*- coding: utf-8 -*-
"""
Created on Mon Mar 29 21:18:15 2021

@author: Arie
"""


import pandas as pd
import urllib.request
from bs4 import BeautifulSoup
import numpy as np


# Function to turn BLS tabular data into dataframe
def url_to_df(url):
    f = urllib.request.urlopen(url)
    soup = BeautifulSoup(f, features="html.parser")

    for script in soup(["script", "style"]):
        script.extract()
    
    # get text
    text = soup.get_text()

    table = text.split('\n')
    table2 = [a.split('\t') for a in table]
    table3 = [[b.strip() for b in a] for a in table2]


    df = pd.DataFrame(table3[1:],columns=table3[0])
    return df

def blsToCSV(fpath):
    States = ["Alabama","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","DC","Florida",
            "Georgia","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland",
            "Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","NewHampshire",
            "NewJersey","NewMexico","NewYork","NorthCarolina","NorthDakota","Ohio","Oklahoma","Oregon","Pennsylvania",
            "RhodeIsland","SouthCarolina","SouthDakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington",
            "WestVirginia","Wisconsin","Wyoming"]

    #States = ["Alabama"]
    linkarray = []

    # Return name of all links so that we can match up states with the correct url
    mainpage = urllib.request.urlopen("https://download.bls.gov/pub/time.series/la/")
    soupmain = BeautifulSoup(mainpage, features="html.parser")

    for script in soupmain(["script", "style"]):
            script.extract()

    for link in soupmain.find_all('a'):
        linkarray.append(link.get('href'))

    # Pull series mapping info into df
    series = url_to_df("https://download.bls.gov/pub/time.series/la/la.series")
    series = series[["series_id","area_code","measure_code","series_title"]]

    # Pull area mapping info into df
    area = url_to_df("https://download.bls.gov/pub/time.series/la/la.area")
    area = area[area["area_type_code"] == "F"]
    area = area[["area_code","area_text"]]

    # Pull measure mapping info into df
    measure = url_to_df("https://download.bls.gov/pub/time.series/la/la.measure")

    # Loop through all states to pull in and modify data    
    for i in States:
        print('.', end='', flush=True)
        # Find link for state
        for j in linkarray:
            if i in j:
                url = j
                break
        fullurl = "https://download.bls.gov" + url

        state = url_to_df(fullurl)
        
        # merge series and area data
        series_area = series.merge(area, how = "inner", on = "area_code")
        
        # merge in state data
        state_series_area = state.merge(series_area, how = "inner", on = "series_id").merge(measure, how = "inner", on = "measure_code")
        
        # Filter on measure codes for unemployment rate and labor force
        state_series_area = state_series_area[state_series_area["measure_code"].isin(["03","06"])]
        
        # Remove yearly averages
        state_series_area = state_series_area[state_series_area["period"] != "M13"]
        
        # Remove missing data
        state_series_area = state_series_area[state_series_area["value"] != "-"]
        
        # Create month variable
        state_series_area["Month"] = state_series_area.apply(lambda x: int(x["period"][1:]), axis = 1)
        
        # Create date variable
        state_series_area["Date"] = state_series_area.apply(lambda x:str(x["Month"]) + "/" "1/" + str(x["year"]),axis = 1)
        state_series_area['Date']= pd.to_datetime(state_series_area['Date'])
        
        # Split out region and state
        state_series_area['Region'] = state_series_area.apply(lambda x: x["area_text"].split(",")[0], axis = 1)
        state_series_area['State'] = state_series_area.apply(lambda x: x["area_text"].split(",")[1] if i != "DC" else "DC", axis = 1)
        
        # Pull FIPS code from area_code
        state_series_area['FIPS'] = state_series_area.apply(lambda x: str(x["area_code"][2:7]), axis = 1)
        
        # Convert value to numeric field
        state_series_area['value'] = state_series_area['value'].astype(np.float64)
        
        # Keep only needed columns
        state_series_area = state_series_area[["FIPS","Region","State","measure_text","Date","value"]]
        
        # Pivot table to get column for each numeric variable
        state_series_area = pd.pivot_table(state_series_area, index=["FIPS","Region","State","Date"], columns="measure_text", values="value").reset_index()
        
        
        
        
        # Combine state data into single df
        if States.index(i) == 0:
            fulldata = state_series_area.copy()
        else:
            fulldata = fulldata.append(state_series_area)
    
    print('.')
    # Export to csv
    fulldata.to_csv(fpath,index=False)

    #a =  pd.pivot_table(fulldata, index=["FIPS","Region","State"], columns="Date", values="labor force").reset_index()
    #b =  pd.pivot_table(fulldata, index=["FIPS","Region","State"], columns="Date", values="unemployment rate").reset_index()
    pass




