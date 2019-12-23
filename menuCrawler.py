# !/usr/bin/env python
# -*- coding: utf-8 -*-
""" Loads different Menus from ETH and UZH and stores them in MongoDB"""
import logging
import pickle
import time
from datetime import date, datetime
from datetime import timedelta

import feedparser
from pylogging import HandlerType, setup_logger
from pymongo import MongoClient

import menu_loader.eth_menu_loader as eth_loader
import menu_loader.street_food_loader as sf_loader
import menu_loader.uzh_menu_loader as uzh_loader
import menu_loader.street_food_loader_html as html_streetfood_loader
import menu_loader.custom_loader as custom_loader
from menu_loader import meat_detector, claras_loader

logger = logging.getLogger(__name__)
setup_logger(log_directory='./logs', file_handler_type=HandlerType.ROTATING_FILE_HANDLER, allow_console_logging=True,
             console_log_level=logging.DEBUG, max_file_size_bytes=1000000)

meatDetector = meat_detector.MeatDetector()


def insert(dictObject, db):
    """ Inserts a given menu Object into the menus database.<br>
    If an object with the current id, date, mensaName and lang allready exists, it will be updated """

    res = db["menus"].update_one(
        {"id": dictObject["id"],
         "date": dictObject["date"],
         "mensaName": dictObject["mensaName"],
         "lang": dictObject["lang"]
         }, {"$set": dictObject}, upsert=True)

    print("modifed: id: " + str(dictObject["id"].encode('utf-8')) + " Date: " + dictObject["date"] + " lang: " +
          dictObject["lang"])
    if res.upserted_id is None:
        print("res: modified: " + str(res.modified_count) + " matched: " + str(res.matched_count))
    else:
        print("res: inserted")


def loadUZHMensa(baseDate, uzhConnectionInfo, db):
    """ Loads all meals for all days of the given uzh connection info. <br>
     Stores the resulting mensa in the mensaMapping object."""

    name = uzhConnectionInfo["mensa"]
    mensaCollection = db["mensas"]

    if mensaCollection.count_documents({"name": name}, limit=1) == 0:
        print("Found new mensa - " + str(name.encode('utf-8')))
        mensaCollection.insert_one(
            {"name": name, "category": uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"],
             "isClosed": True, "address": uzhConnectionInfo["address"], "lat": uzhConnectionInfo["lat"], "lng": uzhConnectionInfo["lng"]})

    try:
        for day in range(1, 6):
            for menu in uzh_loader.loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "de",
                                                      db):
                insert(menu, db)
            for menu in uzh_loader.loadUZHMensaForDay(uzhConnectionInfo, baseDate + timedelta(days=day - 1), day, "en",
                                                      db):
                insert(menu, db)

        mensaCollection.update_one({"name": name}, {
            "$set": {"name": name, "category": uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"],
                     "isClosed": False,  "address": uzhConnectionInfo["address"], "lat": uzhConnectionInfo["lat"], "lng": uzhConnectionInfo["lng"]}}, upsert=True)

    except uzh_loader.MensaClosedException:
        mensaCollection.update_one({"name": name}, {
            "$set": {"name": name, "category": uzhConnectionInfo["category"], "openings": uzhConnectionInfo["opening"],
                     "isClosed": True,  "address": uzhConnectionInfo["address"], "lat": uzhConnectionInfo["lat"], "lng": uzhConnectionInfo["lng"]}}, upsert=True)
        print("Got Mensa Closed exception for Mensa: " + str(name.encode('utf-8')))


def loadAllMensasForWeek(mydb, today):
    """
    Loads all Mensas for the current week (or next week if day is saturday / sunday) and stores it into the mensas, menus collection from the provided db
    :param mydb: MongoClient Databse to store the entries
    :param today: current day as date object
    :return: void
    """

    deleteMenusBeforeGivenDate(str(today + timedelta(days = 7)), mydb)
    print("-----------------starting script at: " + str(today) + "----------------------------")

    # Gets the start of the actual week.
    if today.weekday() < 5:
        startOfWeek = today - timedelta(days=today.weekday())

        # Load all UZH Mensas. We can not get UZH Menus for next week
        i = 1
        mensaEntries = uzh_loader.getMensaEntries()
        for connDef in mensaEntries:
            print("Collecting Mensa (" + str(i) + "/" + str(len(mensaEntries)) + ") : " + str(
                connDef["mensa"].encode('utf-8')))
            i = i + 1
            try:
                loadUZHMensa(startOfWeek, connDef, mydb)
            except RuntimeError as e:
                logger.error(e)
    else:
        # It is a weeked. Lets clean up old menus from the db
        lastWeek = today + timedelta(days=- today.weekday())
        deleteMenusBeforeGivenDate(str(lastWeek), mydb)
        # It is saturday or sunday, load menus for next week.
        startOfWeek = today + timedelta(days=7 - today.weekday())

    # ETH Mensa can be loaded for next week
    m_eth_loader = eth_loader.Loader(mydb, meatDetector)
    loadEthMensa(startOfWeek, mydb, m_eth_loader)


    meatList = meatDetector.getMatchedMeatWords()
    meatList.sort()

    with open('meat.log', 'a+', encoding="utf-8") as fp:
        for line in meatList:
            fp.write(line + "\n")


def loadKlaras():
    """ Loads all menüs for Klaras Kitchen from facebook  <br>
        THIS FUNCTION SLEEPS UNTIL KLARAS IS LOADED OR TOO MANY FAILED TRIES. """

    client = MongoClient("localhost", 27017)
    mydb = client["zhmensa"]
    loadKlarasIntoDb(mydb)

def loadKlarasIntoDb(db):
    """ Loads all menüs for Klaras Kitchen from facebook  <br>
        THIS FUNCTION SLEEPS UNTIL KLARAS IS LOADED OR TOO MANY FAILED TRIES. """

    today = date.today()
    if today.weekday() > 4:
        print("Can not load klaras at weekends")
        return

    startOfWeek = date.today() - timedelta(days= today.weekday())
    tries = 0
    startHour = 9
    maxTries = 12

    while tries < maxTries:
        tries += 1

        print("Loading Claras (" + str(tries) + "/" + str(maxTries) + ")")

        klaras_de = claras_loader.Loader(startOfWeek, "de")
        klaras_en = claras_loader.Loader(startOfWeek, "en")

        for e in klaras_de.getAvailableMensas():
            insert_mensa(e, db)
            print(("found"))
            print(e)
            insert_all([menu.toDict() for menu in klaras_de.getMenusForMensa(e)], db)

        foundMenu = klaras_de.hasMenuForDay(date.today())

        if foundMenu:
            for e in klaras_en.getAvailableMensas():
                insert_all([menu.toDict() for menu in klaras_en.getMenusForMensa(e)], db)
            return

        if datetime.now().hour < startHour:
            print("started script before " + str(startHour) + ". Could not find any menu. Sleeping until " + str(startHour))

            while datetime.now().hour < startHour:
                time.sleep(60*5)
        else:
            time.sleep(60 * 20)

        print("Trying again : (" + str(tries) + "/" + str(maxTries) + ")")

    print("could not load claras. Stopping execution")

def insert_mensa(entry: custom_loader.CustomMensaEntry, db):
    db["mensas"].update_one({"name": entry.name},
                            {"$set": {"name": entry.name, "category": entry.category,
                                      "openings": entry.openings, 'isClosed': not entry.isOpen,
                                      "address": entry.address, "lat": entry.lat, "lng": entry.lng
                                      }},
                            upsert=True)


def loadEthStreetFoodForParams(lang, basedate, day, db):
    """
    :param lang: Language string <de,en>
    :param basedate: The basedate (Monday) as date object
    :param day: which day to load (int), 0 = Monday
    :param db: MongoClient database to insert menus and mensas
    :return: void
    """
    currDate = basedate + timedelta(days=day)

    for mensa in sf_loader.getAvaiableMensas(currDate):

        db["mensas"].update_one({"name": mensa["name"]},
                                {"$set": {"name": mensa["name"], "category": mensa["category"],
                                          "openings": mensa["openings"]}},
                                upsert=True)

        for entry in sf_loader.getMeals(day, lang, currDate, mensa["name"]):
            insert(entry, db)


def insert_all(entry_list, db):
    """ Inserts all entries of the entry_list into the menus database"""
    for entry in entry_list:
        insert(entry, db)


def loadEthMensa(startOfWeek, db, m_eth_loader):
    """ Loads all mensas for a week starting at startOfWeek. <br>
        Stores them in menus DB. Also adds an Entry to the Mensa db if a new mensa is found """
    for i in range(0, 5):
        insert_all(m_eth_loader.loadEthMensaForParams("de", startOfWeek, i, "lunch", i), db)
        insert_all(m_eth_loader.loadEthMensaForParams("de", startOfWeek, i, "dinner", i), db)
        insert_all(m_eth_loader.loadEthMensaForParams("en", startOfWeek, i, "lunch", i), db)
        insert_all(m_eth_loader.loadEthMensaForParams("en", startOfWeek, i, "dinner", i), db)

        loadEthStreetFoodForParams("de", startOfWeek, i, db)
        loadEthStreetFoodForParams("en", startOfWeek, i, db)

    streetFoodLoader = html_streetfood_loader.Loader("de", startOfWeek, meatDetector)

    for mensa in streetFoodLoader.getAvailableMensas():
        insert_mensa(mensa, db)
        insert_all(streetFoodLoader.getMenusForMensa(mensa), db)
    time.sleep(5)

    streetFoodLoader = html_streetfood_loader.Loader("en", startOfWeek, meatDetector)

    for mensa in streetFoodLoader.getAvailableMensas():
        insert_mensa(mensa, db)
        insert_all(streetFoodLoader.getMenusForMensa(mensa), db)

    mensaNamesWithMeals = db["menus"].distinct("mensaName", {"origin": "ETH", "date": {"$gte": str(startOfWeek)}})
    mensaNamesWithMeals.extend(
        db["menus"].distinct("mensaName", {"origin": "ETH-Streetfood", "date": {"$gte": str(startOfWeek)}}))
    allEthMenasList = db["mensas"].distinct("name", {"category": {"$in": ["ETH-Zentrum", "ETH-Hönggerberg"]}})

    # Set Mensa to closed if no meals were found for the given week
    for mensa in allEthMenasList:
        closed = not mensa in mensaNamesWithMeals
        db["mensas"].update_one({"name": mensa}, {"$set": {"isClosed": closed}}, upsert=True)


def deleteMenusBeforeGivenDate(date, db):
    print("date: " + date)
    info = db["menus"].delete_many({"date": {"$lt": date}})
    print("deleted: " + str(info.deleted_count))


def addStringToMeatList(addList):
    """ Adds a string list to the meatlist stored in the meatlist.pickle file"""
    with open('meatlist.pickle', 'rb') as fp:
        meatlist = pickle.load(fp)

    for item in addList:
        meatlist.append(item.lower())
    with open('meatlist.pickle', 'wb') as fp:
        pickle.dump(meatlist, fp)


def removeStringListFromMeatlist(removeList):
    """ Removes a string list from the meatlist stored in the meatlist.pickle file"""
    with open('meatlist.pickle', 'rb') as fp:
        meatlist = pickle.load(fp)

    for item in removeList:
        try:
            meatlist.remove(item.lower()),
        except:
            print("item not found: " + item)
    with open('meatlist.pickle', 'wb') as fp:
        pickle.dump(meatlist, fp)

def removeStringListFromvegiList(removeList):
    """ Removes a string list from the vegilist stored in the vegilist.pickle file"""
    with open('vegilist.pickle', 'rb') as fp:
        list = pickle.load(fp)

    for item in removeList:
        try:
            list.remove(item.lower()),
        except:
            print("item not found: " + item)
    with open('vegilist.pickle', 'wb') as fp:
        pickle.dump(list, fp)


def bruteforce():
    """
    Tries to get all uzh mensas for id [0-1000] and prints it.
    :return: void
    """
    print("bruteforce started")
    for i in range(0, 1000):
        try:
            apiUrl = "https://zfv.ch/de/menus/rssMenuPlan?type=uzh2&menuId=" + str(i) + "&dayOfWeek=1"
            mensaFeed = feedparser.parse(apiUrl)
        except ConnectionError:
            print("error")
            continue

        if 0 != len(mensaFeed.entries):
            entry = mensaFeed.entries[0]
            print(str(i) + " : " + entry["title"])
        else:
            print(str(i) + " : - - -")


def main():
    """Main entry point of the app. """
    client = MongoClient("localhost", 27017)
    mydb = client["zhmensa"]
    today = date.today()
    loadAllMensasForWeek(mydb, today)


if __name__ == '__main__':
    main()
