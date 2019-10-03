# !/usr/bin/env python
# -*- coding: utf-8 -*-
""" Loads different Menus from ETH and UZH and stores them in MongoDB"""
import logging
from pylogging import HandlerType, setup_logger
from datetime import date
import requests
from html.parser import HTMLParser
import feedparser
from pymongo import MongoClient
from datetime import timedelta

logger = logging.getLogger(__name__)

setup_logger(log_directory='./logs', file_handler_type=HandlerType.ROTATING_FILE_HANDLER, allow_console_logging = True, console_log_level  = logging.DEBUG, max_file_size_bytes = 1000000)


class MyHTMLParser(HTMLParser):
    """ Simple HTML Parser that parses the content of the RSS Feed obtained from UZH API """

    def clearState(self):
        self.h3TagReached = False
        self.inNutritionTable = False
        self.currentTag = ""
        self.tdCounter = 0;
        self.spanCounter = 0
        self.pCounter = 0

        self.currentNutritionFact = None;

        self.menuList = []

    def handle_starttag(self, tag, attrs):
        if(tag == "br"):
            # Skip break tagsd
            return

        self.currentTag = tag
        if(tag == "h3"):
            # Begin  menu reached
            self.h3TagReached = True
        elif(tag == "p"):
            self.pCounter = self.pCounter + 1
        elif(tag == "span"):
            self.spanCounter = self.spanCounter + 1
        elif(tag=="img"):
            for attName, attValue in attrs:
                if(self.menu != None and attName == "alt" and (attValue == "vegetarian" or attValue == "vegan" or attValue =="vegetarisch") ):
                    #print(self.menu.name +" : set to vegi" )
                    self.menu.isVegi = True
        elif(tag=="tr"):
            self.inNutritionTable = True

    def parseAndGetMenus(self, htmlToParse):
        self.clearState()
        self.feed(htmlToParse)

        return self.menuList

    def handle_endtag(self, tag):
        if(tag=="tr"):
            self.inNutritionTable = False

        elif(tag =="td"):
            self.tdCounter = self.tdCounter + 1;

    def parsePriceString(self, priceStr):
        print(priceStr)
        priceHolder = priceStr.replace("\n","").replace("|", "").replace("CHF", "").strip().split("/");
        print(priceHolder)
        if(len(priceHolder) == 3):
            self.menu.prices = {"student" : priceHolder[0], "staff": priceHolder[1] , "extern": priceHolder[2]}
        else:
            print("unknown price format" + str(priceStr) + " menu " + self.menu.name)
            self.menu.prices = {}

    def handle_data(self, data):
        if(not self.h3TagReached):
            return

        if (self.currentTag == "h3"):
            self.menu = Menu(data)
            self.menuList.append(self.menu)
            self.spanCounter = 0
            self.pCounter = 0

        elif(self.currentTag == "span"):
            if(self.spanCounter == 1):
                # first span object contains price
                self.parsePriceString(data)
                self.spanCounter = self.spanCounter + 1

        elif(self.currentTag == "p"):
            if(self.pCounter == 1):
                # first <p> contains description
                if(data.strip() != ""):
                    self.menu.description.append(data.replace("\n", "").strip())

            elif(self.pCounter == 2):
                # second <p> contains allergene
                self.menu.allergene = self.menu.allergene + data.replace("Allergikerinformationen:\n", "").replace("Allergikerinformationen:", "").strip()

        elif(self.currentTag == "td" and self.inNutritionTable):
            data = self.trimData(data)
            if(data != ""):
                if(self.tdCounter % 2 == 0):
                    self.currentNutritionFact = {"label" : data}
                    self.menu.nutritionFacts.append(self.currentNutritionFact)
                    # -> Name of nut fact
                elif(self.currentNutritionFact != None):
                    self.currentNutritionFact["value"] = data
            #    None
            #print("in table.")
            #print(data)

    def trimData(self, data):
        if(data == None):
            return data
        else:
            return data.replace("\n", "").strip()


parser = MyHTMLParser()

""" Mapping that maps each ETH Mensa to a given category """
mensaToCategoryMapping = {
    "food market - grill bbQ": "ETH-Hönggerberg",
    "BELLAVISTA": "ETH-Hönggerberg",
    "FUSION meal": "ETH-Hönggerberg",
    "food market - green day": "ETH-Hönggerberg",
    "food market - pizza pasta": "ETH-Hönggerberg"
    }


""" Contains all known API Endpoints """
UZHConnectionDefinitions = [
   {
      "id": 148,
      "mensa": "Obere Mensa B",
      "mealType": "lunch",
      "category": "UZH-Zentrum",
      "meal_openings": None,"opening": None },
   {
      "id": 150,
      "mensa": "Lichthof",
      "mealType": "lunch",
      "category": "UZH-Zentrum"
      ,"meal_openings": None, "opening": None},
   {
      "id": 146,
      "mensa": "Tierspital",
      "mealType": "lunch",
      "category": "UZH-Irchel"
      ,"meal_openings": None,"opening": None },
   {
      "id": 180,
      "mensa": "Irchel",
      "mealType": "lunch",
      "category": "UZH-Irchel"
      ,"meal_openings": None,"opening": None },
   {
      "id": 151,
      "mensa": "Zentrum Für Zahnmedizin",
      "mealType": "lunch",
      "category": "UZH-Zentrum"
      ,"meal_openings": None,"opening": None },
   {
      "id": 143,
      "mensa": "Platte",
      "mealType": "lunch",
      "category": "UZH-Zentrum"
      ,"meal_openings": None,"opening": None },
   {
      "id": 346,
      "mensa": "Rämi 59 (vegan)",
      "mealType": "lunch",
      "category": "UZH-Zentrum"
      ,"meal_openings": None, "opening": None},
   {
      "id": 149,
      "mensa": "Untere Mensa A",
      "mealType": "dinner",
      "category": "UZH-Zentrum"
      ,"meal_openings": None,"opening": None },
   {
      "id": 256,
      "mensa": "Irchel",
      "mealType": "dinner",
      "category": "UZH-Irchel"
      ,"meal_openings": None, "opening": None}
]


def insert(dictObject, db):
    #Update entry if exists
    res = db["menus"].update_one(
        {
            "id": dictObject["id"],
            "date": dictObject["date"],
            "mensaName":dictObject["mensaName"]
        },
        {"$set" : dictObject},
         upsert = True
    )

def loadUZHMensa(baseDate, uzhConnectionInfo, db):
    """ Loads all meals for all days of the given uzh connection info. <br>
     Stores the resulting mensa in the mensaMapping object."""
    name = uzhConnectionInfo["mensa"]

    mensaCollection = db["mensas"]
    if(mensaCollection.count_documents({"name": name}, limit=1) == 0):
        print("Found new mensa - " + str(name.encode('utf-8')))
        mensaCollection.insert_one({"name": name, "category": uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"]})

    for day in range(1, 6):
        loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "de", db)
        loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "en", db)

def bruteforce():
    print("bruteforce started")
    for i in range(0,500):
        apiUrl = "https://zfv.ch/de/menus/rssMenuPlan?type=uzh2&menuId=" + str(i) + "&dayOfWeek=1"
        mensaFeed = feedparser.parse(apiUrl)

        if(len(mensaFeed.entries) != 0):
            entry = mensaFeed.entries[0]
            print(str(i) + " : " + entry["title"])
        else:
            print(str(i) + " : - - -")


def strawpoll():
    # headers = {'User-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/64.0.3282.167 Chrome/64.0.3282.167 Safari/537.36',
    # 'Content-type': 'application/json'}
    # URL = "https://strawpoll.me/api/v2/polls/";
    # payload = {
    #            "title": "This is a.",
    #            "options": [
    #                "Option",
    #                "Option2"
    #            ]
    #         }
    #
    # r = requests.post(url=URL, json=payload, allow_redirects=False).text
    #
    # print(r)
    data = {"title": "Question", "options": ["option1", "option2", "option3"]}
    poll = requests.post("https://www.strawpoll.me/api/v2/polls", json=data,
                         headers={"Content-Type": "application/json"})

    print(poll.url)
    print(poll.text)
    # https://www.strawpoll.me/api/v2/polls
    print(poll.json())
    # {'multi': False, 'title': 'Question', 'votes': [0, 0, 0], 'id': 16578754,
    #  'captcha': False, 'dupcheck': 'normal', 'options': ['option1', 'option2', 'option3']}
def loadUZHMensaForDay(uzhConnectionInfo, date, day, lang, db):
    """ Loads all menus from a given uzhConnectionInfo and day and adds id to the mensa object."""

    apiUrl = "https://zfv.ch/" + lang +"/menus/rssMenuPlan?type=uzh2&menuId=" + str(uzhConnectionInfo["id"]) + "&dayOfWeek="+str(day)
    print("Day: " + str(day) + "/5")

    mensaName = uzhConnectionInfo["mensa"]
    mealType = uzhConnectionInfo["mealType"]

    entry = uzhConnectionInfo["meal_openings"]

    if(entry == None):
        entry = {"from":None, "to": None, "type":mealType}

    entry["mensa"] = mensaName

    db["mealtypes"].update_one(
        {
            "type": entry["type"],
            "mensa": entry["mensa"]
        },
        {"$set" : entry},
         upsert = True
         )
    mensaFeed = feedparser.parse(apiUrl)

    if(len(mensaFeed.entries) == 0):
        raise RuntimeError("Could not find any feed for this connection info and day")

    entry = mensaFeed.entries[0]
    htmlConent = entry.summary

    pos = 0
    for menu in parser.parseAndGetMenus(htmlConent):
        menuName = str(menu.name.encode('utf-8'))
        print("inserting menu: " + menuName + "in db")
        insert(
            {
                "id": getUniqueIdForMenu(mensaName, menu.name, pos, uzhConnectionInfo["mealType"]),
                "mensaName": mensaName,
                "prices": menu.prices,
                "description": menu.description,
                "isVegi": menu.isVegi,
                "allergen": menu.allergene,
                "date": str(date),
                "mealType": mealType,
                "menuName": menu.name,
                "origin": "UZH",
                "nutritionFacts": menu.nutritionFacts,
                "lang": lang
            }, db
        )
        pos = pos + 1


def main():
    """Main entry point of the app. """
    #
    client = MongoClient("localhost", 27017)
    mydb = client["zhmensa"]

    today = date.today()
    print("-----------------starting script at: " + str(today) + "----------------------------")

    # Gets the start of the actual week.
    if (today.weekday() < 5):
        startOfWeek = today - timedelta(days=today.weekday())

        # Load all UZH Mensas. We can not get UZH Menus for next week
        i = 1
        for connDef in UZHConnectionDefinitions:
            print("Collecting Mensa (" + str(i) + "/" + str(len(UZHConnectionDefinitions)) + ") : " + str(connDef["mensa"].encode('utf-8')))
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

        #             {
        #    "title": "This is a test poll.",
        #    "options": [{"mensaId":"1"},{"mensaId":"2"},{"mensaId":"3"}],
        #    "multi": false
        # }
        # if(mensaCollection.count_documents({"name": name}, limit=1) == 0):
        #     print("Found new mensa - " + str(name))

        mensaCollection.update_one({"name" : name}, {"$set" : {"name": name, "category": category, "openings" : hours["opening"]} }, upsert = True)

        meals = mensa["meals"]

    #    for key in hours:
        for entry in  hours["mealtime"]:
            entry["mensa"] = name
            print(entry)
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
            insert(
                {
                    "id": getUniqueIdForMenu(name, meal["label"], pos, type),
                    "mensaName": name,
                    "prices": meal["prices"],
                    "description": meal["description"],
                    "isVegi": isEthVegiMenu(meal),
                    "allergen": meal["allergens"],
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
    return len(origins) == 0;

def loadEthMensa(startOfWeek, db):
    """ Loads all mensas for a week starting at startOfWeek. <br>
        Stores them in menus DB. Also adds an Entry to the Mensa db if a new mensa is found """
    for i in range(0, 5):
        loadEthMensaForParams("de", startOfWeek,  i, "lunch", i, db)
        loadEthMensaForParams("de", startOfWeek,  i, "dinner", i, db)
        loadEthMensaForParams("en", startOfWeek,  i, "lunch", i, db)
        loadEthMensaForParams("en", startOfWeek,  i, "dinner", i, db)


def hasDynamicMenuNames(mensaName):
    """ Returns true if the given mensa changes the name of its menüs. (e.g. Tannebar always renames it's menus)"""
    return mensaName in ["Tannenbar"]


def getUniqueIdForMenu(mensa, menuName, position, mealType):
    """ Creates a unique ID for a given menu """

    if(hasDynamicMenuNames(str(mensa))):
        return "'uni:" + mensa + "' pos: " + str(position) + " mealtype:" + mealType.upper()
    else:
        return "mensa:" + mensa + ",Menu:" + menuName


def deleteMenusBeforeGivenDate(date, db):
    print("date: " + date)
    info = db["menus"].delete_many({"date": {"$lt": date}})
    print("deleted: " + str(info.deleted_count))

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
