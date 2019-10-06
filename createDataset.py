# !/usr/bin/env python
# -*- coding: utf-8 -*-
""" Loads Menus where it is known if they are vegetarian or not and stores them into the file dataset_de.csv"""
import logging
from pylogging import HandlerType, setup_logger
from datetime import date
import requests
from html.parser import HTMLParser
import feedparser
from pymongo import MongoClient
from datetime import timedelta, datetime
from dateutil.parser import parse
from requests.exceptions import ConnectionError

logger = logging.getLogger(__name__)

setup_logger(log_directory='./logs', file_handler_type=HandlerType.ROTATING_FILE_HANDLER, allow_console_logging = True, console_log_level  = logging.DEBUG, max_file_size_bytes = 1000000)


def insert(dictObject, db):
    if(dictObject["isVegi"] is not  None):
        with open('dataset_de.csv','a', encoding='utf-8') as fd:
            if(dictObject["isVegi"]):
                isVegi = 1;
                vegi = "vegi"
            else:
                isVegi = 0
                vegi = "fleisch"

            menuName = str(dictObject["menuName"])
            content = str(" ".join(dictObject["description"]))

            fd.write( "\"" + str(isVegi) + "\"" + ";" + "\"" + vegi + "\"" + ";" + "\"" + menuName + "\";" + "\"" + content + "\"\n")



def main():
    """Main entry point of the app. """
    #

    client = MongoClient("localhost", 27017)
    mydb = client["zhmensa"]
    today = date.today()
    #today =  datetime.strptime("2016-12-17", '%Y-%m-%d').date() ;
    print("-----------------starting script at: " + str(today) + "----------------------------")

    # Gets the start of the actual week.
    if (today.weekday() < 5):
        startOfWeek = today - timedelta(days=today.weekday())
    else:
        # It is saturday or sunday, load menus for next week.
        startOfWeek = today + timedelta(days=7 - today.weekday())

    # startOfWeek = datetime(2019, 8, 28) + timedelta(days = 0)

    for i in range(0, 500):
        print("loading week: " + str(startOfWeek))
        try:
            loadEthMensa(startOfWeek, mydb)
        except ConnectionError:
            print("got error")
        startOfWeek = startOfWeek - timedelta(days= 7)
        # ETH Mensa can be loaded for next week

    # print("inserted: " + str(ins) + " modified: " + str(mod))


def loadDayIntoMensaMap(date, db, mensaMap):
    """Adds all Menus for the given date to the mensa Map"""
    collection = db["menus"]
    mensa = None

    for menu in collection.find({"date": str(date)}).sort("mensaName"):
        if(mensa is None or mensa.name != menu["mensaName"]):
            mensa = mensaMap[menu["mensaName"]]
        mensa.addMenuFromDb(menu, date)


def loadEthMensaForParams(lang, basedate, dayOffset, type, dayOfWeek, db):
    day = basedate + timedelta(days=dayOffset)
    URL = "https://www.webservices.ethz.ch/gastro/v1/RVRI/Q1E1/meals/" + lang + "/" + str(day) + "/" + type

    logger.info("Call url: " + URL)
    r = requests.get(url=URL)
    data = r.json()

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
        #if(name != "Tannenbar"):
        #    continue;

        #print("mensa: " + str(name))
        for meal in meals:
            #print("pos" + str(pos))
            #print("meal:")
            #print(meal)
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

    type = meal["type"]
    if(type != None):
        type = type.lower();
        if("vegan" in type or "vegetarian" in type or "vegetarisch" in type):
            #print("found vegi type in meal " + meal["label"])
            return True;
        if("fish" in type or "fisch" in type or "fleisch" in type or "meat" in type):
            #print("found meat type in meal " + meal["label"])
            return False;

    #print("could not decide vegi for menu " + meal["label"] + " going to analyze origins")
    #print(meal)
    origins= meal["origins"]
    if(len(origins) == 0):
        #print("origins empty for: " + meal["label"])
        return None;
    return False;

def loadEthMensa(startOfWeek, db):
    """ Loads all mensas for a week starting at startOfWeek. <br>
        Stores them in menus DB. Also adds an Entry to the Mensa db if a new mensa is found """
    for i in range(0, 5):
        loadEthMensaForParams("de", startOfWeek,  i, "lunch", i, db)
        loadEthMensaForParams("de", startOfWeek,  i, "dinner", i, db)
        #loadEthMensaForParams("en", startOfWeek,  i, "lunch", i, db)
        #loadEthMensaForParams("en", startOfWeek,  i, "dinner", i, db)


def hasDynamicMenuNames(mensaName):
    """ Returns true if the given mensa changes the name of its menüs. (e.g. Tannebar always renames it's menus)"""
    return mensaName in ["Tannenbar"]


def getUniqueIdForMenu(mensa, menuName, position, mealType):
    """ Creates a unique ID for a given menu """

    if(hasDynamicMenuNames(str(mensa))):
        return "'uni:" + mensa + "' pos: " + str(position) + " mealtype:" + mealType.upper()
    else:
        return "mensa:" + mensa + ",Menu:" + menuName


class Menu:
    def __init__(self, name):
        self.mensa = ""
        self.name = name
        self.id = ""
        self.prices = {}
        self.isVegi = False
        self.allergene = ""
        self.date = None
        self.description = []
        self.nutritionFacts = []


if __name__ == '__main__':
    main()
