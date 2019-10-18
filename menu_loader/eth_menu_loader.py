import json
import pickle
from datetime import timedelta

import requests

mensaToCategoryMapping = {
    """ Mapping that maps each ETH Mensa to a given category """

    "food market - grill bbQ": "ETH-Hönggerberg",
    "BELLAVISTA": "ETH-Hönggerberg",
    "FUSION meal": "ETH-Hönggerberg",
    "food market - green day": "ETH-Hönggerberg",
    "food market - pizza pasta": "ETH-Hönggerberg"
}


class Loader:
    """ Class to load Menus from ETH Web API"""

    def __init__(self, db):
        """
        :param db: The database containing a mensas and mealtypes collection
        """
        self.db = db
        self.loadWordLists()
        self.vegiList_de = []
        self.meatList_de = []
        self.meatmatch = []
        self.loadWordLists()

    def loadWordLists(self):
        """ Loads pickle files into meat and vegi list"""
        with open('vegilist.pickle', 'rb') as fp:
            self.vegiList_de = pickle.load(fp)

        with open('meatlist.pickle', 'rb') as fp:
            self.meatList_de = pickle.load(fp)

    def loadEthMensaForParams(self, lang, basedate, dayOffset, type, dayOfWeek):
        day = basedate + timedelta(days=dayOffset)
        URL = "https://www.webservices.ethz.ch/gastro/v1/RVRI/Q1E1/meals/" + lang + "/" + str(day) + "/" + type

        print("Call url: " + URL)
        loadTries = 0
        while loadTries < 3:
            try:
                r = requests.get(url=URL)
                return self.loadEthMensaForJson(r.json(), day, lang, type)
            except json.decoder.JSONDecodeError:
                print("got JSONDEcodeError for url.")
                print("retrying to get url (" + str(loadTries) + ")")
                loadTries += 1
            except requests.exceptions.ConnectionError:
                print("got Connection Error")
                print("retrying to get url (" + str(loadTries) + ")")
                loadTries += 1

    def loadEthMensaForJson(self, data, day, lang, type):
        list = []
        for mensa in data:
            name = mensa["mensa"]

            mensaCollection = self.db["mensas"]

            hours = mensa["hours"]
            location = mensa["location"]
            if location["id"] == 1:
                category = "ETH-Zentrum"
            elif location["id"] == 2:
                category = "ETH-Hönggerberg"
            else:
                category = "unknown"

            mensaCollection.update_one({"name": name},
                                       {"$set": {"name": name, "category": category, "openings": hours["opening"]}},
                                       upsert=True)

            meals = mensa["meals"]

            #    for key in hours:
            for entry in hours["mealtime"]:
                entry["mensa"] = name
                self.db["mealtypes"].update_one(
                    {
                        "type": entry["type"],
                        "mensa": entry["mensa"]
                    },
                    {"$set": entry},
                    upsert=True
                )

            pos = 0
            for meal in meals:
                allergens = meal["allergens"]
                allergen_arr = []
                for allergen in allergens:
                    allergen_arr.append(allergen["label"])

                list.append(
                    {
                        "id": self.getUniqueIdForMenu(name, meal["label"], pos, type),
                        "mensaName": name,
                        "prices": meal["prices"],
                        "description": meal["description"],
                        "isVegi": self.isEthVegiMenu(meal),
                        "allergen": allergen_arr,
                        "date": str(day),
                        "mealType": type,
                        "menuName": meal["label"],
                        "origin": "ETH",
                        "nutritionFacts": [],
                        "lang": lang
                    }
                )
                pos = pos + 1
        return list

    def isEthVegiMenu(self, meal):
        isVegi = True  # Innocent until proven guilty ;)

        if "grill" in meal["label"]:
            return False;

        type = meal["type"]
        if type != None:
            type = type.lower()
            if "vegan" in type or "vegetarian" in type or "vegetarisch" in type:
                return True;

            if "fish" in type or "fisch" in type or "fleisch" in type or "meat" in type:
                return False;

        origins = meal["origins"]
        if len(origins) != 0:
            return False

        print("Vegi or not is unsure for meal: " + str(meal["label"].encode('utf-8')))

        wordList = []
        for line in meal["description"]:
            wordList.extend(
                line.replace("  ", " ").replace(",", " ").replace("'", "").replace('"', "").replace("&",
                                                                                                    "").lower().split(
                    " "))

        v = 0
        m = 0
        for word in wordList:
            if word == "":
                continue
            elif word in self.meatList_de:
                m += 1
                if not word in self.meatmatch:
                    self.meatmatch.append(word)

            elif word in self.vegiList_de:
                v += 1
        print("score: (m/v) : (" + str(m) + "/" + str(v) + ")")
        print("deciding for: " + str(v >= m))
        return v >= m

    @staticmethod
    def hasDynamicMenuNames(mensaName):
        """ Returns true if the given mensa changes the name of its menüs. (e.g. Tannebar always renames it's menus)"""
        return mensaName in ["Tannenbar", "Foodtrailer ETZ"]

    def getUniqueIdForMenu(self, mensa, menuName, position, mealType):
        """ Creates a unique ID for a given menu """
        # sometimes ETH menus do not have a label if they stored it wrong in the database -.-
        if menuName == "" or self.hasDynamicMenuNames(str(mensa)):
            return "'uni:" + mensa + "' pos: " + str(position) + " mealtype:" + mealType.upper()
        else:
            return "mensa:" + mensa + ",Menu:" + menuName
