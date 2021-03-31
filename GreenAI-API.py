import requests
from requests.auth import HTTPBasicAuth
import json
from flask import Flask, jsonify, make_response, request, render_template, redirect, send_from_directory, url_for
from requests.auth import HTTPBasicAuth
from requests import put, get
from flask_swagger_ui import get_swaggerui_blueprint
import re
import math
import string
import pandas as pd
import os
import subprocess
import io



# Creating base app
app = Flask(__name__)


# defining route for the home page after MS log in
# this has links to either go to docs or get data
# protected by login
@app.route('/home')
def home():
    
    return render_template('start.html')

# route for all documentation
# protected by login
@app.route('/docs_page')
def docs_page():

    return render_template('docs_page.html')

@app.route('/static/<path:path>')
def send_static(path):

    return send_from_directory('static', path)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger7.json'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
    'app_name': "Carbon API testing"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)



# login route to get token to view protected supplying username and password via MSFT creds
@app.route('/login', methods=['GET','POST'])
def login():
    auth = request.authorization
    
    if auth and auth.password == 'mscreds' and auth.username == 'mscreds':
        

        return redirect(url_for('home'))

    return make_response('Could not verify credentials', 401, {'WWW-Authenticate' : 'Basic Portal = "Login Required"'})


# MS authenticated route
# search and thus WattTime connection protected by need for 30 min token from login 
@app.route('/protected', methods=['GET'])
def protected():

    return render_template('az_find.html')


# loading in the .json for the full region set   az_regions.json from Louis. 
    # this is an example output of the look up request CLI command
    # will need changed to active lookup with CLI
#x = open('C:/Users/prewi/OneDrive/Documents/MS-TeamAPI-2021/data/az_regions.json')
#az_coords = json.load(x)

#CLI lookup
az_coords = subprocess.check_output("az account list-locations", shell=True)
az_coords = (az_coords.decode("utf-8"))
az_coords = json.loads(az_coords)

# format as pandas df for usability
az_coords_df = pd.DataFrame(az_coords)


# defining a function to get the username and password from a json file -- added to gitignore
def get_token():
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "static", "login_creds.json")
    login_data = json.load(open(json_url))

    login_url = 'https://api2.watttime.org/v2/login'
    token = requests.get(login_url, auth=HTTPBasicAuth(login_data['username'], login_data['password'])).json()['token']
    return token



# route - Grid Location API
@app.route('/getloc')
def getloc():
    az_region = request.args.get('AZ_Region', None)

    # error handle, if not valid AZ region give 404
    ind_check =[]
    for n in range(len(az_coords)):
        if az_coords[:][n]['displayName'] == az_region:
            ind_check.append(n)
            print(az_coords[n]['displayName'])
        

    # if it is not a valid region it will return and empty list
    if len(ind_check) == 0:
        return make_response(render_template('az_error.html'), 404 )
    

    Key = "displayName"
    Region_Name = az_region
    token = get_token()
    

  # finding coords for the passed AZ_region
    if __name__ == '__main__':

        key = Key
        val = Region_Name
 
        areaDict = next(filter(lambda x: x.get(key) == val, az_coords), None)
        
     
      
    
    #calling coords of AZ region
    AZ_latitude = areaDict['metadata']['latitude']
    AZ_longitude = areaDict['metadata']['longitude']

    # WattTime connection to get ba
    region_url = 'https://api2.watttime.org/v2/ba-from-loc'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'latitude': AZ_latitude, 'longitude': AZ_longitude }
    rsp=requests.get(region_url, headers=headers, params=params)

    # For output interface
    return render_template('datachoice.html', data=json.loads(rsp.text))



# Defining function to calculate great circle distance between two coordinates
def user_distance_to_az(u_lat, u_lon, az_lat, az_lon):
    u_lat_rad = math.radians(u_lat) # Converting lat/lon to radians
    u_lon_rad = math.radians(u_lon)
    az_lat_rad = math.radians(az_lat)
    az_lon_rad = math.radians(az_lon)
    dist = 2*math.asin(math.sqrt((math.sin((u_lat_rad-az_lat_rad)/2))**2+
                                 math.cos(u_lat_rad)*math.cos(az_lat_rad)*
                                 (math.sin((u_lon_rad-az_lon_rad)/2))**2)) # Calculating distance using haversine formula
    return dist


# Finding the nearest AZ region given the coordinates of a user
def nearest_az_region(u_lat, u_lon):
    distToUser = {} # Creating dictionary for storing displayName and distToUser
    
    # Iterating over all stored AZ regions
    for i in az_coords:
        
        # Making sure there is a physical location for region (note that EUAP regions are not processed)
        if i['metadata']['physicalLocation']:
            az_lat = float(i['metadata']['latitude']) # Converting lat/lon to float values
            az_lon = float(i['metadata']['longitude'])
            distToUser[i['displayName']] = user_distance_to_az(u_lat, u_lon, az_lat, az_lon) # Finding the distance to the user and saving in dictionary    
    return(min(distToUser, key=distToUser.get)) # Returning the name of the nearest AZ region


# Creating api route for adding and getting names
#@app.route('/get_region')
#@api.route('/get_region/<string:user_lat>/<string:user_lon>/')
#class AZ_lat_lon(Resource):
@app.route('/get_region')
def get_region():
    u_lat = request.args.get('User_latitude', None)
    u_lon = request.args.get('User_longitude', None)
    u_lat = float(u_lat)
    u_lon = float(u_lon)
    #abort_if_latlon_bad(u_lat, u_lon)	
    AZ_Region = nearest_az_region(u_lat, u_lon)
    for n in range(len(az_coords_df)):
        if az_coords_df['displayName'][n] == AZ_Region:
            ind = n 
            df = WT_Regions
            df = str.strip(re.sub('[^A-Z]', ' ', df[ind][18:40]))
            # check to see if location has a ba
            check = str.strip(WT_Regions[ind][2:7])
            if check == 'error':
                return make_response(render_template('loc_error.html'), 404 ) 
            abbrev = re.sub('[^A-Z]', '_', df)
            sep = '___'
            abbrev = abbrev.split(sep, 1)[0]
            ba = WT_Regions[ind].split("name", 1)[1]
            ba = str.strip(re.sub(r'[\W_]+', ' ', ba))   
            data = {'AZ_Region' : AZ_Region, 'name' : ba ,'abbrev' : abbrev, 'AZ_latitude' : az_coords[ind]['metadata']['latitude'], 
            'AZ_longitude' : az_coords[ind]['metadata']['longitude'], 'id' : no_decimals.sub('', WT_Regions[ind][6:9])}

    
    return render_template('datachoice.html', data=data)
    
# initialization
WT_Regions = []
# loop to associate WattTime regions to AZ regions 
for i in range(len(az_coords)):
    token = get_token()
    region_url = 'https://api2.watttime.org/v2/ba-from-loc'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'latitude': az_coords[i]['metadata']['latitude'],
              'longitude': az_coords[i]['metadata']['longitude']}
    rsp=requests.get(region_url, headers=headers, params=params)
    WT_Regions.append(rsp.text)
    #print(rsp.text)

#combining on index
az_coords_WT_joined = [az_coords, WT_Regions]


# strips values of symbol chars
no_decimals = re.compile(r'[^\d.]+')    

# defining route for starting with ba 
@app.route('/from_ba')
def from_ba():
    df = WT_Regions
    BA_name = request.args.get('ba', None)
    for sublist in df:
        if BA_name in sublist:
            ind = df.index(sublist)
            print(df.index(sublist))
            AZ_Region = (az_coords_WT_joined[0][ind]['displayName'])
            df = str.strip(re.sub('[^A-Z]', ' ', df[ind][18:42]))
            abbrev = re.sub('[^A-Z]', '_', df)
            sep = '___'
            abbrev = abbrev.split(sep, 1)[0]
            data = {'AZ_Region' : AZ_Region, 'name' : BA_name , 'abbrev' : abbrev ,'latitude' : az_coords[ind]['metadata']['latitude'], 
            'longitude' : az_coords[ind]['metadata']['longitude'], 'id' : no_decimals.sub('', WT_Regions[ind][6:9])}
            
            return render_template('datachoice.html', data=data)
        

    # ba has no azure region within it
    return make_response(render_template('ba_error.html'), 404 )    

        

# creating a route selction based on prior dropdown input selection
    # reads value from dropdown and redirects with specified params to next app.route 
@app.route('/chooser', methods=["GET", "POST"])
def chooser():
    choice = request.form['data']
    
    # Grid data path
    if choice == 'grid':
        ba = request.form.get('abbrev', None)
        starttime = request.form.get('starttime', None)
        endtime = request.form.get('endtime', None)
   
        return redirect(url_for('get_grid_data', ba=ba, starttime=starttime, endtime=endtime))
    
    # historical data path, gives zip file
    elif choice == 'historical':
        ba = request.form.get('abbrev', None)
        return redirect(url_for('get_historical_data', ba=ba))

    # real-time data path
    elif choice == 'index':
        ba = request.form.get('abbrev', None)
        return redirect(url_for('get_index_data', ba=ba))

    # marginal emissions forecast data
    elif choice == 'forecast':
        ba = request.form.get('abbrev', None)
        starttime = request.form.get('starttime', None)
        endtime = request.form.get('endtime', None)
        return redirect(url_for('get_forecast_data', ba=ba, starttime=starttime, endtime=endtime))

    # in error or none selected, returns home
    return redirect(url_for('home'))






# @route - '/get_grid_data'
# @method - GET
# @desc - returns point_time, value, frequency, market, ba, datatype, version
@app.route('/get_grid_data', methods=["GET"])
def get_grid_data():
    token = get_token()
    starttime = request.args.get("starttime", None)
    endtime = request.args.get("endtime", None)
    ba = request.args.get("ba", None)
    data_url = 'https://api2.watttime.org/v2/data'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba, 
            'starttime': starttime, 
            'endtime': endtime}
    rsp = requests.get(data_url, headers=headers, params=params)
    return rsp.text # for text output

    #return render_template('output_page.html', data=data)   # for html output

# route to get real-time ba data
@app.route('/get_index_data', methods=["GET"])
def get_index_data():
    token = get_token()
    ba = request.args.get("ba", None)
    index_url  = 'https://api2.watttime.org/index'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba}
    rsp = requests.get(index_url, headers=headers, params=params)
    return rsp.text # for text output

# route to get historical data for given ba
@app.route('/get_historical_data', methods=["GET"])
def get_historical_data():
    token = get_token()
    ba = request.args.get("ba", None)
    historical_url = 'https://api2.watttime.org/v2/historical'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba}
    rsp = requests.get(historical_url, headers=headers, params=params)
    return rsp.text # for text output


# route too get marginal forecast data in designated time window for given ba
@app.route('/get_forecast_data', methods=["GET"])
def get_forecast_data():
    token = get_token()
    starttime = request.args.get("starttime", None)
    endtime = request.args.get("endtime", None)
    ba = request.args.get("ba", None)
    forecast_url = 'https://api2.watttime.org/v2/forecast'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba, 
        'starttime': starttime, 
        'endtime': endtime}
    rsp = requests.get(forecast_url, headers=headers, params=params)
    return rsp.text # for text output

@app.route('/other')
def other():


    return render_template('miro.html')





if __name__ == '__main__':
    app.run(debug=True)