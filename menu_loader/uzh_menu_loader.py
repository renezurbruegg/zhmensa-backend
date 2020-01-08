# !/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103
""" Loads different Menus from ETH and UZH and stores them in MongoDB"""
from html.parser import HTMLParser
import feedparser
from datetime import timedelta
import re

DAYLI_USAGE_MAP = {
    "Calories": 8700,
    "Energie" : 8700,

    "Total Fat":70,
    "Fett":70,

    "Kohlenhydrate":310,
    "Total Carbohydrates":310,

    "Eiweiss":50,
    "Protein":50,
    }

class MensaClosedException(Exception):
   """Raised when parsing of a Uni mensa fails because it is closed"""
   pass

class MyHTMLParser(HTMLParser):
    """ Simple HTML Parser that parses the content of the RSS Feed obtained from UZH API """

    def clearState(self):
        self.h3TagReached = False
        self.inNutritionTable = False
        self.currentTag = ""
        self.tdCounter = 0
        self.spanCounter = 0
        self.pCounter = 0

        self.currentNutritionFact = None

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
        elif(tag == "img"):
            for attName, attValue in attrs:
                if(self.menu != None and attName == "alt" and (attValue == "vegetarian" or attValue == "vegan" or attValue =="vegetarisch") ):
                    # print(self.menu.name +" : set to vegi" )
                    self.menu.isVegi = True
        elif(tag == "tr"):
            self.inNutritionTable = True

    def parseAndGetMenus(self, htmlToParse):
        self.clearState()
        self.feed(htmlToParse)

        if(len(self.menuList) == 0):
            raise MensaClosedException

        return self.menuList

    def handle_endtag(self, tag):
        if(tag=="tr"):
            self.inNutritionTable = False

        elif(tag =="td"):
            self.tdCounter = self.tdCounter + 1;

    def parsePriceString(self, priceStr):
        #print(priceStr)
        priceHolder = priceStr.replace("\n","").replace("|", "").replace("CHF", "").strip().split("/");
        #print(priceHolder)
        if(len(priceHolder) == 3):
            self.menu.prices = {"student" : priceHolder[0], "staff": priceHolder[1] , "extern": priceHolder[2]}
        else:
            #print("unknown price format" + str(priceStr) + " menu " + self.menu.name)
            self.menu.prices = {}

    def handle_data(self, data):
        if(not self.h3TagReached):
            return

        if (self.currentTag == "h3"):
            self.menu = Menu(data)
            self.menu.allergene = []
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
                self.menu.allergene.extend(data.replace("Allergikerinformationen:\n", "").replace("Allergikerinformationen:", "").strip().split(","))

        elif(self.currentTag == "td" and self.inNutritionTable):
            data = self.trimData(data)
            if(data != ""):
                if(self.tdCounter % 2 == 0):
                    self.currentNutritionFact = {"label" : data}
                    self.menu.nutritionFacts.append(self.currentNutritionFact)
                    # -> Name of nut fact
                elif(self.currentNutritionFact != None):
                    self.currentNutritionFact["value"] = data
                    percentage = self.parseNutritionEntryToPercentage(self.currentNutritionFact["label"], data)
                    if(percentage is not None):
                        self.currentNutritionFact["percentage"] = percentage

            #    None
            #print("in table.")
            #print(data)

    def trimData(self, data):
        if(data == None):
            return data
        else:
            return data.replace("\n", "").strip()


    def parseNutritionEntryToPercentage(self, label, valueStr):
        if(valueStr is None):
            return None

        # Parse 1'283 kj (120cal) to 1283
        cleanStr = re.sub("[^\\d.]*", "", re.sub("\\(.+\\)", "", valueStr))
        try:
            amount = float(cleanStr)
            if(label in DAYLI_USAGE_MAP.keys()):
                return int(amount / DAYLI_USAGE_MAP.get(label) * 100)
            else:
                return None
        except:
            return None



vegiList_de = []
meatList_de = []
meatmatch = []
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
    "id_en": 507,
    "mensa": "Obere Mensa B",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 150,
    "id_en": 508,
    "mensa": "Lichthof",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 146,
    "id_en":518,
    "mensa": "Tierspital",
    "mealType": "lunch",
    "category": "UZH-Irchel",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 147,
    "id_en":505,
    "mensa": "Untere Mensa A",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 142,
    "id_en":180,
    "mensa": "Irchel",
    "mealType": "lunch",
    "category": "UZH-Irchel",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 151,
    "id_en":517,
    "mensa": "Zentrum Für Zahnmedizin",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 143,
    "id_en":520,
    "mensa": "Platte",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 176,
    "id_en":512,
    "mensa": "Cafeteria Atrium",
    "mealType": "all_day",
    "category": "UZH-Irchel",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 144,
    "id_en":519,
    "mensa": "Botanischer Garten",
    "mealType": "all_day",
    "category": "UZH-Oerlikon",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 346,
    "id_en":509,
    "mensa": "Rämi 59 (vegan)",
    "mealType": "lunch",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 149,
    "id_en":506,
    "mensa": "Untere Mensa A",
    "mealType": "dinner",
    "category": "UZH-Zentrum",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 184,
    "id_en":515,
    "mensa": "Binzmühle",
    "mealType": "lunch",
    "category": "UZH-Oerlikon",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 241,
    "id_en":513,
    "mensa": "Cafeteria Seerose",
    "mealType": "lunch",
    "category": "UZH-Irchel",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 256,
    "id_en":514,
    "mensa": "Cafeteria Seerose",
    "mealType": "dinner",
    "category": "UZH-Irchel",
    "meal_openings": None,
    "opening": None
  },
  {
    "id": 391,
    "id_en":516,
    "mensa": "Cafeteria Cityport",
    "mealType": "all_day",
    "category": "UZH-Oerlikon",
    "meal_openings": None,
    "opening": None
  }, {
     "id": 303,
     "mensa": "PH Zürich (HB)",
     "mealType": "lunch",
     "category": "others",
     "meal_openings": None,
     "opening": None
  }, {
     "id": 333,
     "mensa": "ZHDK Toni-Areal",
     "mealType": "lunch",
     "category": "others",
     "meal_openings": None,
     "opening": None
  }
]


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
            loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "de", db)
            loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "en", db)

        mensaCollection.update_one({"name" : name}, {"$set" : {"name": name, "category":  uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"], "isClosed" : False} }, upsert = True)

    except MensaClosedException:
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


def loadUZHMensaForDay(uzhConnectionInfo, date, day, lang, db):
    """ Loads all menus from a given uzhConnectionInfo and day and adds id to the mensa object."""

    if(lang == "en" and "id_en" in uzhConnectionInfo.keys()):
        apiUrl = "https://zfv.ch/" + lang +"/menus/rssMenuPlan?type=uzh2&menuId=" + str(uzhConnectionInfo["id_en"]) + "&dayOfWeek="+str(day)
    else:
        apiUrl = "https://zfv.ch/" + lang +"/menus/rssMenuPlan?type=uzh2&menuId=" + str(uzhConnectionInfo["id"]) + "&dayOfWeek="+str(day)

    print("Day: " + str(day) + "/5")
    print("Url: " + str(apiUrl))

    return loadUZHMensaForUrl(uzhConnectionInfo, apiUrl, db, lang, date)



def loadUZHMensaForUrl(uzhConnectionInfo, apiUrl, db, lang, date):
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

    list = []
    for menu in parser.parseAndGetMenus(htmlConent):
        menuName = str(menu.name.encode('utf-8'))
        list.append(
            {
                "id": "mensa:" + mensaName + ",Menu:" + menu.name,
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
            })
    return list

def getMensaEntries():
    return UZHConnectionDefinitions;

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
