# -*- coding: utf-8 -*-
"""
Created on Tue Apr 13 19:55:04 2021

@author: Arie
"""
import pandas as pd 
from fredapi import Fred

def macroVarsToCSV(fpath):
   my_Fred_key = "7596c22502e173dcdb48e96888b3f9a0"
   fred = Fred(api_key=my_Fred_key)
   observation_start='1990-01-01'


   indprod =  fred.get_series('INDPRO', observation_start=observation_start, frequency ="m" )
   indprod  = indprod.to_frame()
   indprod.reset_index(inplace=True)
   indprod = indprod.rename(columns = {'index':'date', 0:'value'})
   indprod['parameter'] = "ind_prod"
   indprod = indprod[['date','parameter','value']]



   sp = fred.get_series('SP500').to_frame()
   sp = sp.resample('1M').last().interpolate()
   sp.index = sp.index.to_series().apply(lambda x: x.replace(day=1))
   sp['chg'] = (sp[0]/sp[0].shift(12)-1)
   sp.reset_index(inplace=True)
   sp = sp.rename(columns = {'index':'date', 'chg':'value'})
   sp['parameter'] = "SP"
   sp = sp.dropna()
   sp = sp[['date','parameter','value']]

   mortgage_rates = fred.get_series("MORTGAGE30US", observation_start=observation_start)
   mortgage_rates = mortgage_rates.to_frame()
   mortgage_rates = mortgage_rates.resample('1M').last().interpolate()
   mortgage_rates.index = mortgage_rates.index.to_series().apply(lambda x: x.replace(day=1))
   mortgage_rates.reset_index(inplace=True)
   mortgage_rates = mortgage_rates.rename(columns = {'index':'date', 0:'value'})
   mortgage_rates['parameter'] = "mortgage_rates"
   mortgage_rates = mortgage_rates[['date','parameter','value']]

   Macro_Var_Data = sp.append(mortgage_rates.append(indprod)).reset_index(drop=True)
   Macro_Var_Data.to_csv(fpath,index=False)


