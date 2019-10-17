# !/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103
""" Loads different Menus from ETH and UZH and stores them in MongoDB"""
import logging
from datetime import date
from html.parser import HTMLParser
import requests
import feedparser
from pymongo import MongoClient
from datetime import timedelta
import pickle
import re
import json
from pylogging import HandlerType, setup_logger
from menu_loader import street_food_loader as sf_loader
from menu_loader import uzh_menu_loader as uzh_loader

logger = logging.getLogger(__name__)
setup_logger(log_directory='./logs', file_handler_type=HandlerType.ROTATING_FILE_HANDLER, allow_console_logging = True, console_log_level  = logging.DEBUG, max_file_size_bytes = 1000000)


vegiList_de = []
meatList_de = []
meatmatch = []


""" Mapping that maps each ETH Mensa to a given category """
mensaToCategoryMapping = {
    "food market - grill bbQ": "ETH-Hönggerberg",
    "BELLAVISTA": "ETH-Hönggerberg",
    "FUSION meal": "ETH-Hönggerberg",
    "food market - green day": "ETH-Hönggerberg",
    "food market - pizza pasta": "ETH-Hönggerberg"
    }


def insert(dictObject, db):
    #Update entry if exists

    res = db["menus"].update_one(
        {
            "id": dictObject["id"],
            "date": dictObject["date"],
            "mensaName":dictObject["mensaName"],
            "lang": dictObject["lang"]
        },
        {"$set" : dictObject},
         upsert = True
    )
    print("modifed: id: " + str(dictObject["id"].encode('utf-8')) + " Date: " +  dictObject["date"] + " lang: " + dictObject["lang"])
    if(res.upserted_id == None):
        print("res: modified: " + str(res.modified_count) + " matched: " + str(res.matched_count))
#        mod = mod + 1
    else:
#        ins = ins + 1
        print("res: inserted")

def loadUZHMensa(baseDate, uzhConnectionInfo, db):
    """ Loads all meals for all days of the given uzh connection info. <br>
     Stores the resulting mensa in the mensaMapping object."""
    name = uzhConnectionInfo["mensa"]

    mensaCollection = db["mensas"]
    if(mensaCollection.count_documents({"name": name}, limit=1) == 0):
        print("Found new mensa - " + str(name.encode('utf-8')))
        mensaCollection.insert_one({"name": name, "category": uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"], "isClosed" : True})

    try:
        for day in range(1, 6):
            for menu in uzh_loader.loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "de", db):
                insert(menu, db)
            for menu in uzh_loader.loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "en", db):
                insert(menu, db)

        mensaCollection.update_one({"name" : name}, {"$set" : {"name": name, "category":  uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"], "isClosed" : False} }, upsert = True)

    except uzh_loader.MensaClosedException:
        mensaCollection.update_one({"name" : name}, {"$set" : {"name": name, "category":  uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"], "isClosed" : True} }, upsert = True)
        print("Got Mensa Closed exception for Mensa: " + str(name.encode('utf-8')))


def bruteforce():
    print("bruteforce started")
    for i in range(0,1000):
        try:
            apiUrl = "https://zfv.ch/de/menus/rssMenuPlan?type=uzh2&menuId=" + str(i) + "&dayOfWeek=1"
            mensaFeed = feedparser.parse(apiUrl)
        except ConnectionError:
            print("error")

        if(len(mensaFeed.entries) != 0):
            entry = mensaFeed.entries[0]
            print(str(i) + " : " + entry["title"])
        else:
            print(str(i) + " : - - -")



def loadWordLists():
    global vegiList_de
    global meatList_de
    with open ('vegilist.pickle', 'rb') as fp:
        vegiList_de = pickle.load(fp)

    with open ('meatlist.pickle', 'rb') as fp:
        meatList_de = pickle.load(fp)



def loadAllMensasForWeek(mydb, today):

    loadWordLists()

    print("-----------------starting script at: " + str(today) + "----------------------------")

    # Gets the start of the actual week.
    if (today.weekday() < 5):
        startOfWeek = today - timedelta(days=today.weekday())

        # Load all UZH Mensas. We can not get UZH Menus for next week
        i = 1
        mensaEntries = uzh_loader.getMensaEntries()
        for connDef in mensaEntries:
            print("Collecting Mensa (" + str(i) + "/" + str(len(mensaEntries)) + ") : " + str(connDef["mensa"].encode('utf-8')))
            i = i + 1
            try:
                 loadUZHMensa(startOfWeek, connDef, mydb)
            except RuntimeError as e:
                logger.error(e)
    else:
        # It is a weeked. Lets clean up old menus from the db
        lastWeek = today + timedelta(days= - today.weekday())
        deleteMenusBeforeGivenDate(str(lastWeek), mydb)
        # It is saturday or sunday, load menus for next week.
        startOfWeek = today + timedelta(days=7 - today.weekday())

    # ETH Mensa can be loaded for next week
    loadEthMensa(startOfWeek, mydb)

    meatmatch.sort()
    with open ('meat.log', 'a+', encoding="utf-8") as fp:
        for line in meatmatch:
            fp.write(line + "\n");


    #print("inserted: " + str(ins) + " modified: " + str(mod))
def main():
    """Main entry point of the app. """
    #

    client = MongoClient("localhost", 27017)
    mydb = client["zhmensa"]
    today = date.today()

    loadAllMensasForWeek(mydb, today)


def loadDayIntoMensaMap(date, db, mensaMap):
    """Adds all Menus for the given date to the mensa Map"""
    collection = db["menus"]
    mensa = None

    for menu in collection.find({"date": str(date)}).sort("mensaName"):
        if(mensa is None or mensa.name != menu["mensaName"]):
            mensa = mensaMap[menu["mensaName"]]
        mensa.addMenuFromDb(menu, date)


def loadEthStreetFoodForParams(lang, basedate, day, db):
    currDate = basedate + timedelta(days = day)

    for mensa in sf_loader.getAvaiableMensas(currDate):

        db["mensas"].update_one({"name" : mensa["name"]},
            {"$set" : {"name": mensa["name"], "category": mensa["category"], "openings" : mensa["openings"]} },
            upsert = True)

        for entry in sf_loader.getMeals(day, lang, currDate, mensa["name"]):
            insert(entry, db)

def loadEthMensaForParams(lang, basedate, dayOffset, type, dayOfWeek, db):
    day = basedate + timedelta(days=dayOffset)
    URL = "https://www.webservices.ethz.ch/gastro/v1/RVRI/Q1E1/meals/" + lang + "/" + str(day) + "/" + type

    print("Call url: " + URL)
    loadTries = 0;
    while(loadTries < 3):
        try:
            r = requests.get(url=URL)
            loadEthMensaForJson(r.json(), db, day, lang, type)
            break
        except json.decoder.JSONDecodeError:
            print("got JSONDEcodeError for url.")
            print("retrying to get url (" + str(loadTries) + ")")
            loadTries+=1
        except requests.exceptions.ConnectionError:
            print("got Connection Error")
            print("retrying to get url (" + str(loadTries) + ")")
            loadTries+=1

def loadEthMensaForJson(data, db,  day, lang, type):
    for mensa in data:
        name = mensa["mensa"]

        mensaCollection = db["mensas"]

        hours = mensa["hours"]
        location = mensa["location"]
        if location["id"] == 1:
            category = "ETH-Zentrum"
        elif location["id"] == 2:
            category = "ETH-Hönggerberg"
        else:
            category = "unknown"

        mensaCollection.update_one({"name" : name}, {"$set" : {"name": name, "category": category, "openings" : hours["opening"]} }, upsert = True)

        meals = mensa["meals"]

    #    for key in hours:
        for entry in  hours["mealtime"]:
            entry["mensa"] = name
            db["mealtypes"].update_one(
                {
                    "type": entry["type"],
                    "mensa": entry["mensa"]
                },
                {"$set" : entry},
                 upsert = True
                 )



        pos = 0
        for meal in meals:
            allergens = meal["allergens"]
            allergen_arr = []
            for allergen in allergens:
                allergen_arr.append(allergen["label"])


            insert(
                {
                    "id": getUniqueIdForMenu(name, meal["label"], pos, type),
                    "mensaName": name,
                    "prices": meal["prices"],
                    "description": meal["description"],
                    "isVegi": isEthVegiMenu(meal),
                    "allergen": allergen_arr,
                    "date": str(day),
                    "mealType": type,
                    "menuName": meal["label"],
                    "origin": "ETH",
                    "nutritionFacts": [],
                    "lang": lang
                }, db
            )
            pos = pos + 1;

def isEthVegiMenu(meal):
    isVegi = True; # Innocent until proven guilty ;)

    if("grill" in meal["label"]):
        return False;

    type = meal["type"]
    if(type != None):
        type = type.lower()
        if("vegan" in type or "vegetarian" in type or "vegetarisch" in type):
            #print("found vegi type in meal " + meal["label"])
            return True;
        if("fish" in type or "fisch" in type or "fleisch" in type or "meat" in type):
            #print("found meat type in meal " + meal["label"])
            return False;

    #print("could not decide vegi for menu " + meal["label"] + " going to analyze origins")
    #print(meal)
    origins= meal["origins"]
    if(len(origins) != 0):
        return False

    print("Vegi or not is unsure for meal: " + str(meal["label"].encode('utf-8')))
    wordList = []
    for line in meal["description"]:
        wordList.extend(line.replace("  "," ").replace(","," ").replace("'","").replace('"',"").replace("&","").lower().split(" "))

    global meatmatch
    v = 0
    m = 0
    for word in wordList:
        if(word ==""):
            continue
        elif(word in meatList_de):
            m += 1
            if(not word in meatmatch):
                meatmatch.append(word)

        elif(word in vegiList_de):
            v += 1
    print("score: (m/v) : (" + str(m) + "/"+str(v)+")")
    print("deciding for: " + str(v>=m))
    return v >= m

def loadEthMensa(startOfWeek, db):
    """ Loads all mensas for a week starting at startOfWeek. <br>
        Stores them in menus DB. Also adds an Entry to the Mensa db if a new mensa is found """
    for i in range(0, 5):
        loadEthMensaForParams("de", startOfWeek,  i, "lunch", i, db)
        loadEthMensaForParams("de", startOfWeek,  i, "dinner", i, db)
        loadEthMensaForParams("en", startOfWeek,  i, "lunch", i, db)
        loadEthMensaForParams("en", startOfWeek,  i, "dinner", i, db)

        loadEthStreetFoodForParams("de", startOfWeek, i, db)
        loadEthStreetFoodForParams("en", startOfWeek, i, db)

    mensaNamesWithMeals = db["menus"].distinct("mensaName", {"origin":"ETH", "date" : {"$gte": str(startOfWeek)}})
    allEthMenasList = db["mensas"].distinct("name", {"category": {"$in" : ["ETH-Zentrum","ETH-Hönggerberg"]}})

    # Set Mensa to closed if no meals were found for the given week
    for mensa in allEthMenasList:
        closed = not mensa in mensaNamesWithMeals
        db["mensas"].update_one({"name" : mensa}, {"$set" : {"isClosed" : closed} }, upsert = True)



def hasDynamicMenuNames(mensaName):
    """ Returns true if the given mensa changes the name of its menüs. (e.g. Tannebar always renames it's menus)"""
    return mensaName in ["Tannenbar", "Foodtrailer ETZ"]


def getUniqueIdForMenu(mensa, menuName, position, mealType):
    """ Creates a unique ID for a given menu """
    # sometimes ETH menus do not have a label if they stored it wrong in the database -.-
    if(menuName == "" or hasDynamicMenuNames(str(mensa))):
        return "'uni:" + mensa + "' pos: " + str(position) + " mealtype:" + mealType.upper()
    else:
        return "mensa:" + mensa + ",Menu:" + menuName


def deleteMenusBeforeGivenDate(date, db):
    print("date: " + date)
    info = db["menus"].delete_many({"date": {"$lt": date}})
    print("deleted: " + str(info.deleted_count))

def addStringToMeatList(addList):
    with open ('meatlist.pickle', 'rb') as fp:
        meatlist = pickle.load(fp)

    for item in addList:
        meatlist.append(item.lower())
    with open('meatlist.pickle', 'wb') as fp:
        pickle.dump(meatlist, fp)

def removeStringListFromMeatlist(removeList):
    with open ('meatlist.pickle', 'rb') as fp:
        meatlist = pickle.load(fp)

    for item in removeList:
        try:
            meatlist.remove(item.lower()),
        except:
            print("item not found: " + item)
    with open('meatlist.pickle', 'wb') as fp:
        pickle.dump(meatlist, fp)

class Menu:
    def __init__(self, name):
        self.mensa = ""
        self.name = name
        self.id = ""
        self.prices = {}
        self.isVegi = False
        self.allergene = []
        self.date = None
        self.description = []
        self.nutritionFacts = []


if __name__ == '__main__':
    main()
