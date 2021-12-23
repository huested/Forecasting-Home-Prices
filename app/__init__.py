import os

from flask import Flask
from flask import render_template
from flask import g
from flask import url_for
from flask import request
from flask import jsonify
import numpy as np
from .db import *

def create_app(test_config=None):
   # Create and configure app
   app = Flask(__name__, instance_relative_config=True)
   app.config.from_mapping(
   SECRET_KEY='temp',
   DATABASE=os.path.join(app.instance_path, 'cse6242.sqlite'),
)

   # Initialize db
   from . import db

   db.init_app(app)

   # Ensure the instance folder exists
   try:
      os.makedirs(app.instance_path)
   except OSError:
      pass

   # Main page
   @app.route('/main', methods=('GET', 'POST'))
   def main():
      return render_template('./main.html')

   # County price data
   @app.route('/countyprices/<string:fips>')
   def getCountyPrices(fips):
      county_prices = getSingleCountyPrices(fips)
      return jsonify(county_prices)

   # Unique FIPS data
   @app.route('/fiplist')
   def getFipList():
      fip_list = getCountyList()
      return jsonify(fip_list)

   # Unemployment data
   @app.route('/unemployment/<string:fips>')
   def getUnemployment(fips):
      unemployment_data = getSingleCountyUnemployment(fips)
      return jsonify(unemployment_data)

   # Labor data
   @app.route('/labor/<string:fips>')
   def getLabor(fips):
      labor_data = getSingleCountyLabor(fips)
      return jsonify(labor_data)

   # Macro sp data
   @app.route('/sp')
   def getSP():
      sp_data = getMacroSP()
      return jsonify(sp_data)
   
   # Macro mortgage data
   @app.route('/mortgage')
   def getMortgageRates():
      mortgage_data = getMacroMortgage()
      return jsonify(mortgage_data)  

   # Macro ind prod data
   @app.route('/indprod')
   def getIndProd():
      ind_prod_data = getMacroIndProd()
      return jsonify(ind_prod_data) 

   # Predicted prices 
   @app.route('/predict/<string:fips>/<string:sp>/<string:unemp>/<string:mort>/<string:ip>/<string:lab>')
   def getPrediction(fips,sp,unemp,mort,ip,lab):
      sp = float(sp)/100.0
      lab = float(lab)/100.0
      unemp=float(unemp)
      mort=float(mort)
      ip=float(ip)
      user_array = np.asarray([sp,unemp,mort,ip,lab])
      preds = getPredictedPrice(fips, user_array)
      return jsonify(preds)

   # Example route
   @app.route('/test2/<string:fips>')
   def test2(fips):
      test_return = "example second data structure for fips " + str(fips)
      return jsonify(test_return)

   return app