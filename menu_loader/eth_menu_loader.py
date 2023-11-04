import json
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



mensas = json.load(open("menu_loader/eth_mensa_info.json", "r"))

# mensas = [
#     #{"id": "2", "name": "bQm", "cat": "ETH-Zentrum"},
#     #{"id": "3", "name": "CafeBar", "cat": "ETH-Zentrum"},
#     {"id": "4", "name": "Clausiusbar", "cat": "ETH-Zentrum"},
#     #{"id": "5", "name": "Kiosk CLA", "cat": "ETH-Zentrum"},
#     {"id": "6", "name": "Dozentenfoyer", "cat": "ETH-Zentrum"},
#     #{"id": "7", "name": "Einstein & Zweistein", "cat": "ETH-Zentrum"},
#     {"id": "9", "name": "Foodtrailer ETZ", "cat": "ETH-Zentrum"},
#     #{"id": "10", "name": "Kiosk ETZ", "cat": "ETH-Zentrum"},
#     {"id": "11", "name": "G-ESSbar", "cat": "ETH-Zentrum"},
#     {"id": "12", "name": "Mensa Polyterrasse", "cat": "ETH-Zentrum"},
#     {"id": "13", "name": "Polysnack", "cat": "ETH-Zentrum"},
#     {"id": "14", "name": "Tannenbar", "cat": "ETH-Zentrum"},
#     {"id": "15", "name": "Alumni quattro Lounge", "cat": "ETH-Hönggerberg"},
#     #{"id": "17", "name": "Bistro HPI", "cat": "ETH-Hönggerberg"},
#     {"id": "18", "name": "food market - pizza pasta", "cat": "ETH-Hönggerberg"},
#     {"id": "19", "name": "food market - green day", "cat": "ETH-Hönggerberg"},
#     {"id": "20", "name": "food market - grill bbQ", "cat": "ETH-Hönggerberg"},
#     {"id": "21", "name": "FUSION meal", "cat": "ETH-Hönggerberg"},
#     {"id": "22", "name": "FUSION coffee", "cat": "ETH-Hönggerberg"},
#     {"id": "25", "name": "BELLAVISTA", "cat": "ETH-Hönggerberg"},
#     #{"id": "26", "name": "Zwei Grad Bistro", "cat": "ETH-Zentrum"},
#     #{"id": "27", "name": "Rice Up!", "cat": "ETH-Hönggerberg"},
#     {"id": "28", "name": "food&lab", "cat": "ETH-Zentrum"}
# ]

class Loader:
    """ Class to load Menus from ETH Web API"""

    def __init__(self, db, meatDetector):
        """
        :param db: The database containing a mensas and mealtypes collection
        """
        self.db = db
        self.meatDetector = meatDetector
        with open('menu_loader/ethLocations.json', 'r',  encoding="utf-8") as fp:
            self.locationDict = json.load(fp)


    def loadEthMensaForParams(self, lang, basedate, dayOffset, type, dayOfWeek):
        list = []
        for entry in mensas:
            try:
                print("PROCESSING", entry, "with", dayOfWeek)
                list.extend(self. loadEthMensaForParamsWithId(lang, basedate, dayOffset, type, dayOfWeek, entry['facility-id'], entry["cat"]))
            except Exception as e:
                print(">====================\n", "Could not process ", entry, "error", e, "\n=====================================")
        return list

    def loadEthMensaForParamsWithId(self, lang, basedate, dayOffset, type, dayOfWeek, id, category):
        day = basedate + timedelta(days=dayOffset + 1)
        day_before = day -  timedelta(days=1)
        # id = 3
        URL = f"https://idapps.ethz.ch/cookpit-pub-services/v1/weeklyrotas/?client-id=ethz-wcms&lang={lang}&rs-first=0&rs-size=500&valid-after={day_before}&valid-before={day}&facility={id}"
        print(URL)

        # URL = "testhttps://www.webservices.ethz.ch/gastro/v1/RVRI/Q1E1/mensas/"+str(id)+"/"+lang+"/menus/daily/"+str(day)+"/"+type;
        #URL = "https://www.webservices.ethz.ch/gastro/v1/RVRI/Q1E1/meals/" + lang + "/" + str(day) + "/" + type

        print("Call url: " + URL)
        loadTries = 0
        while loadTries < 3:
            try:
                r = requests.get(url=URL)
                return self.loadEthMensaForJson(r.json(), day_before, lang, type, category, dayOffset)
            except json.decoder.JSONDecodeError:
                print("got JSONDEcodeError for url.")
                print("retrying to get url (" + str(loadTries) + ")")
                loadTries += 1
            except requests.exceptions.ConnectionError:
                print("got Connection Error")
                print("retrying to get url (" + str(loadTries) + ")")
                loadTries += 1


    def loadEthMensaForParamsOLD(self, lang, basedate, dayOffset, type, dayOfWeek):
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


    def parsePriceArray(self, price_arr):
        ret = ""
        for line in price_arr:
            ret += line["customer-group-desc-short"] + " " + str(line["price"]) + ".- / "
        if len(ret) > 2:
            ret = ret[:-2]
        return ret

    def loadEthMensaForJson(self, mensa, day, lang, type, category="ETH-Zentrum", dayOffset= 0):
        list = []
        
        data = mensa["weekly-rota-array"]
        hours = ""
        name = "?"
        pos = 0

        locationEntry = {"address": None, "lat": None, "lng": None}


        parsed_meals = []
        for entry in data:
        
            mensa_id = entry["facility-id"]
            for m in mensas:
                if m["facility-id"] == mensa_id:
                    name = m["facility-name"] 
                    locationEntry = {}
                    break

            for meal_each_day in entry["day-of-week-array"]:
                if meal_each_day["day-of-week-code"] != dayOffset + 1:
                    continue
                
                for meal_time in meal_each_day["opening-hour-array"]:
                    for meal in meal_time["meal-time-array"]:
                        hours = meal_time["time-from"] + "-" + meal_time["time-to"]
                        for m in meal["line-array"]:
                            full_meal = m["meal"]
                            meal_name = m["name"]
                            
                            our_meal_entry = {
                                "id": self.getUniqueIdForMenu(name, meal_name, pos, type),
                                "mensaName": name,
                                "prices": self.parsePriceArray(full_meal["meal-price-array"]),
                                "description": full_meal["description"],
                                "isVegi": "meal-class-array" not in full_meal or (("Vegan" in str(full_meal["meal-class-array"])) or ("Vegetarian" in str(full_meal["meal-class-array"]))),
                                "allergen": "",
                                "date": str(day),
                                "mealType": type,
                                "menuName": meal_name,
                                "origin": "ETH",
                                "nutritionFacts": [],
                                "lang": lang
                            }
                            parsed_meals.append(our_meal_entry)
                            pos += 1

        return parsed_meals


        name = mensa["mensa"]

        mensaCollection = self.db["mensas"]

        hours = mensa["hours"]
        """location = mensa["location"]
        if location["id"] == 1:
            category = "ETH-Zentrum"
        elif location["id"] == 2:
            category = "ETH-Hönggerberg"
        else:
            category = "unknown" """

        # locationEntry = self.getLocationEntryForMensaName(name)
        mensaCollection.update_one({"name": name},
                                   {"$set":
                                        {"name": name,
                                         "category": category,
                                         "openings": hours["opening"],
                                         "address": locationEntry["address"],
                                         "lat": locationEntry["lat"],
                                         "lng": locationEntry["lng"],
                                         }},
                                   upsert=True)
        if ('menu' not in mensa):
            print("No Menu found!")
            return []

        menu = mensa['menu']
        meals = menu["meals"]

        #    for key in hours:
        # Dirty fix
        """ ent = entry["mealtypes"]
        type = ""
        if ent is not None:
            for e in ent:
                type = e['label']
                break

        for entry in hours["mealtime"]:
            entry["mensa"] = name
            self.db["mealtypes"].update_one(
                {
                    "type": type,
                    "mensa": entry["mensa"]
                },
                {"$set": entry},
                upsert=True
            )"""

        pos = 0
        for meal in meals:
            if meal["description"] == "" or meal["description"] == []:
                print("description was empty. Going to skip meal")
                continue

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
            return False
        # Dirty fix
        type = ""
        for e in meal["mealtypes"]:
            type = e["label"]

        if type is not None:
            type = type.lower()
            if "vegan" in type or "vegetarian" in type or "vegetarisch" in type:
                return True

            if "fish" in type or "fisch" in type or "fleisch" in type or "meat" in type:
                return False

        origins = meal["origins"]
        if len(origins) != 0:
            return False

        print("Vegi or not is unsure for meal: " + str(meal["label"].encode('utf-8')))
        return not self.meatDetector.containsMeat(meal["description"])

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

    def getLocationEntryForMensaName(self, mensaName):
        if mensaName in self.locationDict.keys():
            return self.locationDict[mensaName]
        else:
            return {"address": None, "lat": None, "lng": None}
