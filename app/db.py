import sqlite3
import pandas as pd 
import click
from flask import current_app, g
from flask.cli import with_appcontext
from sqlite3 import Error
from pathlib import Path
import urllib
from bs4 import BeautifulSoup
from .scripts.BLSDataScript import blsToCSV
from .scripts.MacroVarDataScript import macroVarsToCSV
import numpy as np
from dateutil.relativedelta import relativedelta

#
# 
#
# Data import to sqlite functions
#
#
#

# zillow county price table
def create_county_price_table(conn):
   print("create_county_price_table: Creating county_prices table...")
   # Read csv
   zillow_df = pd.read_csv(str(Path(__file__).resolve().parent) + "/data/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_mon.csv")
   # Transpose wide to long (each column is price of particular date)
   zillow_columns = zillow_df.columns.tolist()
   cols_id = zillow_columns[:9]
   cols_transpose = zillow_columns[9:]
   zillow_df_long = pd.melt(zillow_df, id_vars=cols_id, value_vars=cols_transpose, var_name='date', value_name='price')
   # Create date variables
   zillow_df_long['date'] = pd.to_datetime(zillow_df_long['date'], format='%m/%d/%y', infer_datetime_format=True)
   zillow_df_long.sort_values(['StateCodeFIPS', 'MunicipalCodeFIPS', 'date'], inplace=True)
   zillow_df_long['year'], zillow_df_long['month'] = zillow_df_long['date'].dt.year, zillow_df_long['date'].dt.month
   # Create fips variable
   zillow_df_long['stateFipsStr'] = zillow_df_long['StateCodeFIPS'].astype(str).str.zfill(2)
   zillow_df_long['countyFipsStr'] = zillow_df_long['MunicipalCodeFIPS'].astype(str).str.zfill(3)
   zillow_df_long['fipsStr'] = zillow_df_long['stateFipsStr'] + zillow_df_long['countyFipsStr']
   # Drop rows where price is missing
   zillow_df_long.dropna(subset=['price'], inplace=True)
   zillow_df_long.to_sql('county_prices', con=conn, if_exists='replace')
   num_obs = conn.execute('SELECT COUNT(*) FROM county_prices').fetchone()[0]
   print("create_county_price_table: Created county_prices table with " + str(num_obs) + " rows")


def create_bls_tables(conn):
   print("create_bls_table: Creating BLS tables...")
   fpath = str(Path(__file__).resolve().parent) + "/data/Full_BLS.csv"
   bls_file = Path(fpath)
   if bls_file.is_file():
      pass
   else:
      print("create_bls_table: /data/Full_BLS.csv not found, creating csv")
      blsToCSV(fpath)
      print("create_bls_table: /data/Full_BLS.csv created")
   bls_df = pd.read_csv(fpath)
   bls_df['fipsStr'] = bls_df['FIPS'].astype(str).str.zfill(5)
   bls_df['Date'] = pd.to_datetime(bls_df['Date'], format='%Y-%m-%d', infer_datetime_format=True)
   bls_df['year'], bls_df['month'] = bls_df['Date'].dt.year, bls_df['Date'].dt.month
   bls_df.rename({'labor force': 'labor_force', 'unemployment rate': 'unemployment_rate', 'Date': 'date'}, axis=1, inplace=True)
   bls_df.sort_values(['fipsStr', 'date'], ascending=[True, True], inplace=True)
   # Separate table for each variable & drop missings
   labor_df = bls_df[['fipsStr', 'date', 'year', 'month', 'labor_force']].dropna(subset=['labor_force'])
   unemployment_df = bls_df[['fipsStr', 'date', 'year', 'month', 'unemployment_rate']].dropna(subset=['unemployment_rate'])
   # To sqlite
   labor_df.to_sql('county_labor', con=conn, if_exists='replace')
   unemployment_df.to_sql('county_unemployment', con=conn, if_exists='replace')
   num_obs_labor = conn.execute('SELECT COUNT(*) FROM county_labor').fetchone()[0]
   num_obs_unemployment = conn.execute('SELECT COUNT(*) FROM county_unemployment').fetchone()[0]
   print("create_bls_table: Created county_labor table with " + str(num_obs_labor) + " rows")
   print("create_bls_table: Created county_unemployment table with " + str(num_obs_unemployment) + " rows")


def create_macro_tables(conn):
   print("create_macro_tables: Creating macro variable tables...")
   fpath = str(Path(__file__).resolve().parent) + "/data/Macro_Var.csv"
   macro_file = Path(fpath)
   if macro_file.is_file():
      pass
   else:
      print("create_macro_tables: /data/Macro_Var.csv not found, creating csv")
      macroVarsToCSV(fpath)
      print("create_macro_tables: /data/Macro_Var.csv created")
   macro_df = pd.read_csv(fpath)
   macro_df['date'] = pd.to_datetime(macro_df['date'], format='%-m/%-d/%Y', infer_datetime_format=True)
   macro_df['year'], macro_df['month'] = macro_df['date'].dt.year, macro_df['date'].dt.month
   macro_df.sort_values(['parameter', 'date'], ascending=[True, True], inplace=True)
   #print(macro_df.dtypes)
   # Create table per variable
   sp_df = macro_df.loc[macro_df['parameter'] == 'SP'].dropna(subset=['value'])
   mortgage_df = macro_df.loc[macro_df['parameter'] == 'mortgage_rates'].dropna(subset=['value'])
   ind_prod_df = macro_df.loc[macro_df['parameter'] == 'ind_prod'].dropna(subset=['value'])
   # To sqlite
   sp_df.to_sql('macro_sp', con=conn, if_exists='replace')
   mortgage_df.to_sql('macro_mortgage', con=conn, if_exists='replace')
   ind_prod_df.to_sql('macro_ind_prod', con=conn, if_exists='replace')
   # Print rows created
   num_obs_sp = conn.execute('SELECT COUNT(*) FROM macro_sp').fetchone()[0]
   num_obs_mortgage = conn.execute('SELECT COUNT(*) FROM macro_mortgage').fetchone()[0]
   num_obs_ind_prod = conn.execute('SELECT COUNT(*) FROM macro_ind_prod').fetchone()[0]
   print("create_macro_tables: Created macro_sp table with " + str(num_obs_sp) + " rows")
   print("create_macro_tables: Created macro_mortgage table with " + str(num_obs_mortgage) + " rows")
   print("create_macro_tables: Created macro_ind_prod table with " + str(num_obs_ind_prod) + " rows")

def create_model_tables(conn):
   print("create_model_tables: Creating model tables")
   # Means
      # Read
   means_wide_df = pd.read_csv(str(Path(__file__).resolve().parent) + "/data/model_means.csv")
      # Transpose fips columns wide to long
   means_wide_columns = means_wide_df.columns.tolist()
   cols_id = means_wide_columns[0]
   cols_transpose = means_wide_columns[1:]
   means_transpose_1 = pd.melt(means_wide_df, id_vars=cols_id, value_vars=cols_transpose, var_name='fips', value_name='value')
      # Transpose variable
   means_df = means_transpose_1.pivot(index='fips', columns=cols_id, values='value')
      # Reassign index to fips that is zero padded
   new_index = means_df.index.to_frame(index=False, name='fips')
   new_index['fips'] = new_index['fips'].astype(str).str.zfill(5)
   means_df.index = new_index.fips
   means_df.sort_values(['fips'], ascending=[True], inplace=True)
      # To sql
   means_df.to_sql('model_means', con=conn, if_exists='replace')
   num_obs_means = conn.execute('SELECT COUNT(*) FROM model_means').fetchone()[0]
   print("create_model_tables: Created model_means table with " + str(num_obs_means) + " rows")

   
   # Standard deviations
      # Read
   std_wide_df = pd.read_csv(str(Path(__file__).resolve().parent) + "/data/model_stddevs.csv")
      # Transpose fips columns wide to long
   std_wide_columns = std_wide_df.columns.tolist()
   cols_id = std_wide_columns[0]
   cols_transpose = std_wide_columns[1:]
   std_transpose_1 = pd.melt(std_wide_df, id_vars=cols_id, value_vars=cols_transpose, var_name='fips', value_name='value')
      # Transpose variable
   std_df = std_transpose_1.pivot(index='fips', columns=cols_id, values='value')
      # Reassign index to fips that is zero padded
   new_index = std_df.index.to_frame(index=False, name='fips')
   new_index['fips'] = new_index['fips'].astype(str).str.zfill(5)
   std_df.index = new_index.fips
      # To sql
   std_df.to_sql('model_stds', con=conn, if_exists='replace')
   num_obs_std = conn.execute('SELECT COUNT(*) FROM model_stds').fetchone()[0]
   print("create_model_tables: Created model_stds table with " + str(num_obs_std) + " rows")
   

   # Parameters
   params = pd.read_csv(str(Path(__file__).resolve().parent) + "/data/model_params.csv")
   params['fips'] = params['fips'].astype(str).str.zfill(5)
   params.set_index('fips', inplace=True)
   params.to_sql('model_params', con=conn, if_exists='replace')
   num_obs_std = conn.execute('SELECT COUNT(*) FROM model_params').fetchone()[0]
   print("create_model_tables: Created model_params table with " + str(num_obs_std) + " rows")


   #padded_fips = '06037'
   # np.array([0.05, 6, 4.5, 110, 0.03])
   # (datetime.datetime(2022, 1, 31, 0, 0), 2022, 1, 770153.9669262235



#
# 
#
# Flask functions
#
#
#

def get_db():
   if 'db' not in g:
      g.db = sqlite3.connect(
         current_app.config['DATABASE'],
         detect_types=sqlite3.PARSE_DECLTYPES
      )
      #g.db.row_factory = sqlite3.Row

   return g.db

def close_db(e=None):
   db = g.pop('db', None)
   if db is not None:
      db.close()

def init_db():
   db = get_db()
   create_county_price_table(db)
   create_bls_tables(db)
   create_macro_tables(db)
   create_model_tables(db)

@click.command('init-db')
@with_appcontext
def init_db_command():
   """Clear the existing data and create new tables."""
   click.echo('init-db: Initializing database...')
   init_db()
   click.echo('init-db: Database initialized.')

@click.command('print-cols')
@click.argument('table_name')
@with_appcontext
def db_schemas_command(table_name):
   db = get_db()
   cursor = db.cursor()
   cursor.execute("select * from %s" % table_name)
   names = list(map(lambda x: x[0], cursor.description))
   cursor.close()
   print(names)
   

def init_app(app):
   app.teardown_appcontext(close_db)
   app.cli.add_command(init_db_command)
   app.cli.add_command(db_schemas_command)


#
# 
#
# Query functions
#
#
#


# Input: fips code
# Output: [fips, date, year, month, price]
def getSingleCountyPrices(fips):
   db = get_db()
   padded_fips = str(fips).zfill(5)
   single_county_prices = db.execute('select date, year, month, price from county_prices where fipsStr = ? order by fipsStr, date', (padded_fips,)).fetchall()
   return single_county_prices

# Input: None
# Output: [fips, state_name, county_name]
def getCountyList():
   db = get_db()
   fips_codes = db.execute('select distinct fipsStr, StateName, RegionName from county_prices order by fipsStr').fetchall()
   return fips_codes

# Input: fips code
# Output: [fips, date, year, month, unemployment]
def getSingleCountyUnemployment(fips):
   db = get_db()
   padded_fips = str(fips).zfill(5)
   single_county_unemployment = db.execute('select date, year, month, unemployment_rate from county_unemployment where fipsStr = ? order by fipsStr, Date', (padded_fips,)).fetchall()
   return single_county_unemployment

# Input: fips code
# Output: [fips, date, year, month, labor]
def getSingleCountyLabor(fips):
   db = get_db()
   padded_fips = str(fips).zfill(5)
   single_county_labor = db.execute('select date, year, month, labor_force from county_labor where fipsStr = ? order by fipsStr, Date', (padded_fips,)).fetchall()
   return single_county_labor

# Input: None
# Output [date, year, month, sp]
def getMacroSP():
   db = get_db()
   macro_sp = db.execute('select date, year, month, value from macro_sp order by date').fetchall()
   return macro_sp

# Input: None
# Output [date, year, month, mortgage rate]
def getMacroMortgage():
   db = get_db()
   macro_mortgage = db.execute('select date, year, month, value from macro_mortgage order by date').fetchall()
   return macro_mortgage

# Input: None
# Output [date, year, month, mortgage rate]
def getMacroIndProd():
   db = get_db()
   macro_ind_prod = db.execute('select date, year, month, value from macro_ind_prod order by date').fetchall()
   return macro_ind_prod


# Input: Fips, user arguments
# Output [date, year, month, price]
def getPredictedPrice(fips, user_array):
   fips = str(fips).zfill(5)
   db = get_db()

   # Get means, stddevs, and parameters from the model tables
   means = np.asarray(db.execute('select SP,unemployment,mortgage_rates,ind_prod,labor_force from model_means where fips = ?', (fips,)).fetchall()[0])
   stds = np.asarray(db.execute('select SP,unemployment,mortgage_rates,ind_prod,labor_force from model_stds where fips = ?', (fips,)).fetchall()[0])
   params = np.asarray(db.execute('select intercept,arima_error,SP,unemployment,mortgage_rates,ind_prod,labor_force from model_params where fips = ?', (fips,)).fetchall()[0])
   # Calculate forecast
   intercept = params[0]
   arima_error = params[1]
   params = params[2:]
   norm_values = (user_array - means)/stds
   forecast = intercept + arima_error + sum(params*norm_values)

   # Append prediction to price data
   prices = db.execute('select date,year,month,price from county_prices where fipsStr = ? order by date', (fips,)).fetchall()
   last_price = prices[-1]
   pred_date = last_price[0] + relativedelta(years=1)
   pred_year = pred_date.year
   pred_month = pred_date.month
   pred_price = round(last_price[3]*(1.0+forecast),1)
   pred = (pred_date, pred_year, pred_month, pred_price)
   prices.append(pred)
   return prices