# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""Entry point for the server application."""
import json
import logging
import os
import traceback
from datetime import date
from datetime import timedelta, datetime
from functools import update_wrapper

from bson.objectid import ObjectId
from flask import make_response
from flask import request, current_app, Flask
from flask_cors import CORS
from flask_jwt_simple import (
    JWTManager
)
import collections
from pylogging import HandlerType, setup_logger
from pymongo import MongoClient

from .config import CONFIG
from .http_codes import Status

logger = logging.getLogger(__name__)
setup_logger(log_directory='./logs', file_handler_type=HandlerType.ROTATING_FILE_HANDLER, allow_console_logging = True, console_log_level  = logging.DEBUG, max_file_size_bytes = 1000000)

app = Flask(__name__)
# Load Configuration for app. Secret key etc.
config_name = os.getenv('FLASK_CONFIGURATION', 'default')

app.config.from_object(CONFIG[config_name])

# Set Cors header. Used to accept connections from browser using XHTTP requests.
CORS(app, headers=['Content-Type'])
jwt = JWTManager(app)

mensaMapping = {}

mydb = MongoClient("localhost", 27017)["zhmensa"]

pollsDb = MongoClient("localhost", 27017)["zhmensa_polls"]

def main():
    """Main entry point of the app. """

    logger.info("starting server")
    try:
        app.run(debug = True, host = app.config["IP"], port = app.config["PORT"])
        logger.info("Server started. IP: " + str(app.config["IP"]) + " Port: " + str(app.config["PORT"]))
    except Exception as exc:
        logger.error(exc)
        logger.exception(traceback.format_exc())
    finally:
        pass



def loadMensaMapFromDb(db):
    today = date.today()

    if(today.weekday() < 5):
        startOfWeek = today - timedelta(days = today.weekday())
    else: # It is saturday or sunday, load menus for next weekl
        startOfWeek = today + timedelta(days = -today.weekday())

    mensaMap = getEmptyMensaMapFromDb(db)

    for day in range(5):
        loadDayIntoMensaMap(startOfWeek + timedelta(days=day), db, mensaMap)

    json_data = json.dumps(mensaMap, cls=CustomJsonEncoder,indent=2, sort_keys=False)
    print(json_data)


@jwt.jwt_data_loader
def add_claims_to_access_token(identity):
    """ Used to allow CORS Request from any source"""
    now = datetime.utcnow()
    return {
        'exp': now + current_app.config['JWT_EXPIRES'],
        'iat': now,
        'nbf': now,
        'sub': identity,
        'roles': 'Admin'
    }


def crossdomain(origin=None, methods=None, headers=None, max_age=21600,
                attach_to_all=True, automatic_options=True):
    """Decorator function that allows crossdomain requests.
      Courtesy of
      https://blog.skyred.fi/articles/better-crossdomain-snippet-for-flask.html
    """
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    # use str instead of basestring if using Python 3.x
    if headers is not None and not isinstance(headers, list):
        headers = ', '.join(x.upper() for x in headers)
    # use str instead of basestring if using Python 3.x
    if not isinstance(origin, list):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        """ Determines which methods are allowed
        """
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        """The decorator function
        """
        def wrapped_function(*args, **kwargs):
            """Caries out the actual cross domain code
            """
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Content-type'] = "application/json"
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            h['Access-Control-Allow-Headers'] = \
                "Origin, X-Requested-With, Content-Type, Accept, Authorization"
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator



class CustomJsonEncoder(json.JSONEncoder):
    """ Custom Json Encoder that encodes Mensa, weekdays, (...) obj. to JSON """
    def default(self, o):
        # Here you can serialize your object depending of its type
        # or you can define a method in your class which serializes the object
        if isinstance(o, (Mensa, Weekday, MealType, Menu)):
            return o.__dict__  # Or another method to serialize it
        else:
            return json.JSONEncoder.encode(self, o)




"""
@app.route('/api/debug', methods=['POST', 'OPTIONS'])
def debug():
    filter = request.json;

    list = []
    for menu in mydb["menus"].find(filter):
        del menu["_id"]
        list.append(menu)

    json_data = json.dumps(list, indent=2, sort_keys=False)
    return json_data, Status.HTTP_OK_BASIC;
"""


# -------- POLL API ROUTES -----------------------


@app.route('/api/polls', methods=['POST', 'OPTIONS'])
@crossdomain(origin = '*')
def getPollsForPayload():
    """
    ### API Path   `/api/polls`
    ### Request Type: `POST`
    Returns all Poll objects matching the id's in post request body.
    """

    jsonPayload = request.json;

    print(jsonPayload)
    lookupIds = jsonPayload["ids"]

    print("got ids: " + str(lookupIds))


    collection = pollsDb["polls"]
    idFilter = [ObjectId(id) for id in lookupIds]
    print("filter :" + str(idFilter))

    list = []

    for res in collection.find({"_id" : {"$in":idFilter}}):
        res["id"] = str(res["_id"])
        del res["_id"]
        list.append(res);
        #return  json.dumps(res ,indent=2, sort_keys=False), Status.HTTP_OK_BASIC

    return json.dumps({"polls" : list} ,indent=2, sort_keys=False), Status.HTTP_OK_BASIC

@app.route('/api/polls/<id>', methods=['GET', 'OPTIONS'])
@crossdomain(origin = '*')
def getPollForId(id):
    """
    ### API Path   `/api/poll/<id>`
    ### Request Type: `GET`
    Returns the poll for the given id
    """


    collection = pollsDb["polls"]

    for res in collection.find({"_id" :  ObjectId(id)}):
        res["id"] = str(res["_id"])
        del res["_id"]
        return  json.dumps(res ,indent=2, sort_keys=False), Status.HTTP_OK_BASIC

    return "ID not found", Status.HTTP_BAD_NOTFOUND






@app.route('/api/polls/vote/<id>', methods=['POST', 'OPTIONS'])
@crossdomain(origin = '*')
def addVoteForId(id):
    """
    ### API Path   `/api/polls/vote/<id>`
    ### Request Type: `POST`
    Performs a vote action on the given Poll.
    ### Request Body:
        "votes" : [
            {
                "mensaId": "<mensaId>",
                "menuId": "<menuId>",
                "voteType": "<positive/negative>"
            } ,
            { ... }
        ],
        "update": <true/false>`
    """

    if(request.json is None):
        return "Payload missing", Status.HTTP_BAD_REQUEST

    try:
        votes = request.json["votes"]
        update = request.json["update"]
    except KeyError as e:
        return "Payload corrupt", Status.HTTP_BAD_REQUEST

    if(votes is None):
        return "Payload corrupt", Status.HTTP_BAD_REQUEST


    collection = pollsDb["polls"]
    result = None

    id = ObjectId(str(id))

    for res in collection.find({"_id" : id}):
        result = res

    if result is None:
        return "ID not found", Status.HTTP_BAD_NOTFOUND

    for option in result["options"]:
        for vote in votes:
            if (vote["mensaId"] == option["mensaId"] and vote["menuId"] == option["menuId"]):
                if(vote["voteType"] == "positive"):
                    option["votes"] = option["votes"] + 1
                elif(vote["voteType"] == "negative"):
                    option["votes"] = max(0, option["votes"] - 1)
    if (not update):
        result["votecount"] = result["votecount"] + 1

    collection.update_one({"_id" : id}, {"$set" : result}, upsert = False)

    return getPollForId(str(id))




@app.route('/api/polls/update/<id>', methods=['POST', 'OPTIONS'])
@crossdomain(origin = '*')
def updatePoll(id):
    """
    ### API Path   `/api/polls/update/<id>`
    ### Request Type: `POST`
    Updates a given Poll.

    Payload Example:

        {
	       "title": "new Vote",
	       "weekday":0,
	       "mealType":"lunch",

	       "options": [
	       {
	       "mensaId": "testMensa", "menuId": "testMenu"

	       },
	       {
	          "mensaId": "testMensa", "menuId": "testMenu2"
	       }
	       ]
        }
    """


    if(request.json is None):
        return "Payload missing", Status.HTTP_BAD_REQUEST
    payload = request.json

    try:
        title = str(payload["title"])
        options = payload["options"]
        weekday = payload["weekday"]
        mealType = payload["mealType"]
    except KeyError as e:
        return "Payload corrupt", Status.HTTP_BAD_REQUEST

    if(options is None):
        return "Payload corrupt", Status.HTTP_BAD_REQUEST


    collection = pollsDb["polls"]
    result = None

    id = ObjectId(str(id))

    for res in collection.find({"_id" : id}):
        result = res

    if result is None:
        return "ID not found", Status.HTTP_BAD_NOTFOUND

    result["title"] = title
    result["weekday"] = weekday
    result["mealType"] = mealType

    newOptions = []

    for option in options:
        foundOption = False

        for storedOpt in result["options"]:
            if(storedOpt["mensaId"] == option["mensaId"] and storedOpt["menuId"] == option["menuId"]):
                newOptions.append(storedOpt)
                foundOption = True
                break

        if(not foundOption):
            newOptions.append({"mensaId" : option["mensaId"], "menuId" : option["menuId"], "votes" : 0});

    result["options"] = newOptions

    collection.update_one({"_id" : id}, {"$set" : result}, upsert = False)

    return getPollForId(str(id))




@app.route('/api/polls/create', methods=['POST', 'OPTIONS'])
@crossdomain(origin = '*')
def createNewPoll():
    """
    ### API Path   `/api/polls/create`
    ### Request Type: `POST`
    Creates a new Poll for the given mensa id's

    Payload Example:

        {
    	"title": "new Vote",
    	"weekday":0,
    	"mealType":"lunch",
    	"options": [
    		{
    			"mensaId": "testMensa", "menuId": "testMenu"

    		},
    		{
    			"mensaId": "testMensa", "menuId": "testMenu2"
    		}
    		]
        }
    """
    # TODO saniitaze inputs
    payload = request.json;
    if(payload is None):
        return "Payload missing", Status.HTTP_BAD_REQUEST

    try:
        title = str(payload["title"])
        options = payload["options"]
        weekday = payload["weekday"]
        mealType = payload["mealType"]

    except KeyError as e:
        return "Payload corrupt", Status.HTTP_BAD_REQUEST


    if(title is None or options is None):
        return "Payload corrupt", Status.HTTP_BAD_REQUEST
    #{"ids" : ["5d56d4eb3d073cd0be878449","5d5ac35dcf51f20dbf43b2a8", "5d5ac367cf51f20dbf43b2a9"]}

    optionsToStore = []
    for option in options:
        optionsToStore.append({"mensaId" : option["mensaId"], "menuId" : option["menuId"], "votes" : 0})
        # try:
        #     option["votes"] = 0;
        #     if("mensaId" not in option):
        #         return "Payload corrupt", Status.HTTP_BAD_REQUEST
        # except TypeError as e:
        #     return "Payload corrupt", Status.HTTP_BAD_REQUEST


    collection = pollsDb["polls"]
    today = date.today()

    id = collection.insert_one({"title" : title, "mealType" : mealType, "weekday" : weekday, "votecount" : 0,  "options": optionsToStore, "creationdate": str(today)})

    json_data = json.dumps(payload ,indent=2, sort_keys=False)
    print(json_data)
    return "{ \"id\":\"" + str(id.inserted_id)+"\"}", Status.HTTP_OK_BASIC;


# -------- END POLL API ROUTES -----------------------

@app.route('/api/getMensaForTimespan', methods=['GET', 'OPTIONS'])
@crossdomain(origin = '*')
def getMensaForTimespan():
    """
    ### API Path   `/api/getAllMensas`
    ### Request Type: `GET`
    Returns all mensas for the actual week
    """
    startDay = request.args.get('start')
    endDay = request.args.get('end')


    startTimeDate = datetime.strptime(startDay, '%Y-%m-%d').date()
    endTimeDate = datetime.strptime(endDay, '%Y-%m-%d').date()

    json_data = json.dumps( loadMensaFromDateToDate(mydb, startTimeDate, endTimeDate), cls=CustomJsonEncoder,indent=2, sort_keys=False)
    return json_data, Status.HTTP_OK_BASIC;




@app.route('/api/getMensaForCurrentWeek', methods=['GET', 'OPTIONS'])
@crossdomain(origin = '*')
def getMensaForCurrentWeek():
    """
    ### API Path   `/api/getAllMensas`
    ### Request Type: `GET`
    Returns all mensas for the actual week
    """
    json_data = json.dumps( loadMensaMapForCurrentWeek(mydb), cls=CustomJsonEncoder,indent=2, sort_keys=False)
    return json_data, Status.HTTP_OK_BASIC;

@app.route('/api/<lang>/<category>/getMensaForCurrentWeek',  methods=['GET', 'OPTIONS'])
@crossdomain(origin = '*')
def getMensaForLangCatCurrWeek(lang, category):
    """
    ### API Path   `/api/<lang>/<category>/getMensaForCurrentWeek`
    ### Request Type: `GET`
    Returns all mensas for the actual week that match a given category and contain menus in the given language.

    if all is used as category, all categories are returned
    """

    json_data = json.dumps(loadMensaMapForCurrentWeek(mydb, lang, category), cls=CustomJsonEncoder,indent=2, sort_keys=False)

    return json_data, Status.HTTP_OK_BASIC;




class Mensa:
    def __init__(self, jsonObject):
        self.name = jsonObject["name"]
        self.weekdays = {}
        self.openings = jsonObject["openings"]
        self.category = jsonObject["category"]
        self.isClosed = jsonObject["isClosed"]
        self.location = {
            "address": jsonObject.get("address"),
            "lat": jsonObject.get("lat"),
            "lng": jsonObject.get("lng"),
        }


    def setWeek(self, date):
        self.loadedWeek = str(date)

    def addMenuFromDb(self, menuDbObject, date, db):
        if(str(date) not in self.weekdays):
            self.weekdays[str(date)] = Weekday(date, "type?", date.strftime("%A"), date.weekday())

        day = self.weekdays[str(date)]
        day.addMenu(menuDbObject, self.name, db)

    def addWeekday(self, weekday):
        for day in self.weekdays:
            if(day.label == weekday.label):
                day.addMealTypeFromDay(weekday)
                return
        self.weekdays.append(weekday)



class Weekday:
    def __init__(self, date, type, weekday, weekdayNumber):
        self.number = weekdayNumber
        self.label = weekday
        self.mealTypes = {}

        self.date = str(date)

    def addMenu(self, menuDbObject, mensaName, db):
        typeName = menuDbObject["mealType"]

        if(typeName not in self.mealTypes):
            self.mealTypes[typeName] = MealType(menuDbObject["mealType"], mensaName, db)

        self.mealTypes[typeName].addMenu(Menu(menuDbObject))


    def addMealTypeFromDay(self, day):
        for mType in day.mealTypes:
            self.mealTypes.append(mType)

class MealType:
    def __init__(self, label, mensa, db):
        self.label = label

        self.hours = {
            "from" : None,
            "to": None
        }
        collection = db["mealtypes"]

        for mealtype in collection.find({"mensa": mensa, "type": label}):
            self.hours = {
                "from" : mealtype["from"],
                "to": mealtype["to"]
            }

        self.menus = []

    def addMenu(self, menu):
        self.menus.append(menu)

class Menu:
    def __init__(self, menuDbObject):
        self.mensa = menuDbObject["mensaName"]
        self.name = menuDbObject["menuName"]
        self.id = menuDbObject["id"]
        self.prices = menuDbObject["prices"]
        self.description = menuDbObject["description"]
        self.isVegi = menuDbObject["isVegi"]
        self.allergene = menuDbObject["allergen"]
        self.date = menuDbObject["date"]
        self.nutritionFacts = menuDbObject["nutritionFacts"]
        self.meta = {}

        if "link" in menuDbObject:
            self.meta["link"] = menuDbObject["link"]

def loadDayIntoMensaMap(date, db, mensaMap, lang):
    """Adds all Menus for the given date to the mensa Map"""
    collection = db["menus"]
    mensa = None
    filterObj = {"date": str(date), "lang": lang}
    print("loadDayIntoMensaMap lang" + lang)

    for menu in collection.find(filterObj).sort("mensaName"):

        if(menu["mensaName"] in mensaMap):
            if(mensa is None or mensa.name != menu["mensaName"]):
                mensa = mensaMap[menu["mensaName"]]
            if(mensa != None):
                mensa.addMenuFromDb(menu, date, db)


def getEmptyMensaMapFromDb(db, category):
    """ creates an empty mensa map containing empty mensa objects for each menesa"""
    mensaMap = collections.OrderedDict();
    filter = {}
    if(category != "all"):
        filter= {"category": category}

    for mensa in db["mensas"].find(filter).sort( "name", 1):
        mensaMap[mensa["name"]] = Mensa(mensa)

    return mensaMap


def loadMensaFromDateToDate(db, startDate, endDate):
    """ Loads all Menus for the current week into a mensa map [mensaName <=> MensaObject] and returns it"""
    dates = []
    while startDate <= endDate:
        if(startDate.weekday() > 4):
            startDate = startDate + timedelta(days = 1)
            print(startDate)
            continue #Skip weekends

        dates.append(startDate);
        startDate = startDate + timedelta(days = 1)
        print(startDate)
    #
    # dayDiff = startDate.day
    # dates = [startOfWeek + timedelta(days=i) for i in range(5)]
    print(dates)
    return loadMensaMapForGivenDatesFromDb(db, dates , None)


def loadMensaMapForCurrentWeek(db, lang = "de", category = "all"):
    """ Loads all Menus for the current week into a mensa map [mensaName <=> MensaObject] and returns it"""
    today = date.today()

    if(today.weekday() < 5):
        startOfWeek = today - timedelta(days=today.weekday())
    else:
        # It is saturday or sunday, load menus for next weekl
        startOfWeek = today + timedelta(days=-today.weekday() + 7)

    dates = [startOfWeek + timedelta(days=i) for i in range(5)]

    return loadMensaMapForGivenDatesFromDb(db, dates , None, lang, category)


def loadMensaMapForGivenDatesFromDb(db, datesList, mensaMap, lang="de", category="all"):
    """ Loads all menus for the given dates inside the given mensamap and returns it. If mensaMap is None a new one will be returned"""
    if(mensaMap is None):
        mensaMap = getEmptyMensaMapFromDb(db, category)

    for mDate in datesList:
        print("loading menus for date:" + str(mDate))
        loadDayIntoMensaMap(mDate, db, mensaMap, lang)

    return mensaMap
