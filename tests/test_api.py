import os
import sys

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

import json
import warnings

from pymongo import MongoClient
from datetime import date

from datetime import timedelta

import menuCrawler as crawler
# noinspection PyUnresolvedReferences
from checkMenuEntries import VALID_RSS_MENU_ENTRIES, VALID_JSON_MENU_ENTRIES_LUNCH, VALID_JSON_MENU_ENTRIES_DINNER

import flask_app.server as server

import menu_loader.uzh_menu_loader as uzh_loader
import menu_loader.eth_menu_loader as eth_loader
import menu_loader.meat_detector as meat_detector
import menu_loader.street_food_loader_html as html



TESTING_DATABASE = "zhmensa_testing"
MENUS = "menus"
MENSAS = "mensas"
POLL_DATABASE = "zhmensa_testing_polls"


db = MongoClient("localhost", 27017)[TESTING_DATABASE]
pollDb = MongoClient("localhost", 27017)[POLL_DATABASE]

server.mydb = db
server.pollsDb = pollDb

"""def test_food():
    det = meat_detector.MeatDetector()
    basedate = date.today() - timedelta(days = date.today().weekday())
    p = html.Loader("de", basedate, det)
    for m in p.getAvailableMensas():
        print("---m----")
        for me in p.getMenusForMensa(m):
            print(me)
    for l in det.getMatchedMeatWords():
        print(l)
    print("vegi")
    for l in det.getMatchedVegiWords():
        print(l)
    assert False"""


def testReadStaticMenuUZH():

    db[MENUS].drop()
    db[MENSAS].drop()
    """ Tests if a static UZH RSS feed entry will be parsed correctly"""

    UZH_CONNECTION_INFO = {
        "id": 146,
        "mensa": "Tierspital",
        "mealType": "lunch",
        "category": "UZH-Irchel",
        "meal_openings": None,
        "opening": None
      }

    for menu in uzh_loader.loadUZHMensaForUrl(UZH_CONNECTION_INFO, "./tests/rssMenuPlan.html", db, "de", "2019-10-10"):
        crawler.insert(menu, db)

    for entry in VALID_RSS_MENU_ENTRIES:
        record  = db[MENUS].find(entry)
        assert record != None


#def testReadStaticMenuETHLunch():
    """Tests if a static ETH Lunch json will be parsed correctly"""

    """
    with open('./tests/eth_lunch_2019_07_05.json', encoding="utf-8") as f:
        content = json.loads(f.read())
        loader = eth_loader.Loader(db, meat_detector.MeatDetector())
        crawler.insert_all(loader.loadEthMensaForJson(content, "2019-07-05", "de", "lunch"), db)

    for entry in VALID_JSON_MENU_ENTRIES_LUNCH:
        if(db[MENUS].find_one(entry) is None):
            print("--------------------------")
            print("Could not find entry in db")
            print(entry)
            print("found: ")
            for e in db[MENUS].find({"id": str(entry['id'])}):
                print(e)
            assert False
    """


#def testReadStaticMenuETHDinner():
    """ Tests if a static ETH Dinner json will be parsed correctly"""
    """
    with open('./tests/eth_dinner_2019_07_05.json', encoding="utf-8") as f:
        content = json.loads(f.read())
        loader = eth_loader.Loader(db, meat_detector.MeatDetector())
        crawler.insert_all(loader.loadEthMensaForJson(content, "2019-07-05", "de", "dinner"), db)

    for entry in VALID_JSON_MENU_ENTRIES_DINNER:
        if db[MENUS].find_one(entry) is None:
            print("--------------------------")
            print("Could not find entry in db")
            print(entry)
            assert False
    """

def testReadCurrentWeek():
    db[MENUS].drop()

    today = date.today() - timedelta(days = date.today().weekday())
    crawler.loadAllMensasForWeek(db, today)

    """ The ETH API does not always have entry for every day. Also sometimes menus are missing. Define a max missing count"""
    maxMissingDays = 20

    for d in range(0,5):
        currDate = today + timedelta(days=d)
        for lang in ["de", "en"]:
            for mealType in  ["lunch","dinner"]:
                for origin in ["ETH", "UZH"]:
                    if db[MENUS].find_one({"date":str(currDate), "lang": lang, "origin": origin, "mealType":mealType}) is None:
                        warnings.warn("Could not find entry for day " + str(currDate) +" lang " + lang + " type " + mealType + " origin: " + origin)
                        maxMissingDays -= 1;
                        if(maxMissingDays == 0):
                            assert False

def testGetForTimespanApi():
    client = server.app.test_client()
    today = date.today() - timedelta(days = date.today().weekday())
    end = today + timedelta(days = 5)

    resp = client.get("/api/getMensaForTimespan?start="+str(today) + "&end="+str(end))
    assert resp.status_code == 200
    respJson = resp.json
    assert len(respJson) != 0

    for mensa in respJson:
        daysList = respJson[mensa]["weekdays"]

        if(len(daysList) == 0):
            if(respJson[mensa]["isClosed"] != True):
                print("Found empty day list for Mensa and it was not closed Mensa: " + mensa)
                assert False

        elif(len(daysList) != 5):
            warnings.warn(UserWarning("Daylist for mensa " + mensa + " did not have length 5"))


def testCreatePoll():
    client = server.app.test_client()
    payload = {
        "title": "TestVote",
        "weekday": 2,
        "mealType":"lunch",
        "options": [
            {
                "mensaId": "testMensa1", "menuId": "testMenu1"

            },
            {
                "mensaId": "testMensa2", "menuId": "testMenu2"
            }
            ]
    }
    resp = client.post('/api/polls/create', data= json.dumps(payload), content_type='application/json')


    assert resp.status_code == 200
    id = resp.json["id"]

    resp = client.get('/api/polls/'+id)
    assert resp.status_code == 200

    payload = {
        "votes" : [
            {
                "mensaId": "testMensa1",
                "menuId": "testMenu1",
                "voteType": "positive"
            },
        ],
        "update": False
    }

    resp = client.post('/api/polls/vote/'+id,  data= json.dumps(payload), content_type='application/json')


    print(resp.json)
    assert resp.json["votecount"] == 1
    for entry in resp.json["options"]:
        if(entry["mensaId"] == "testMensa1"):
            assert entry["votes"] == 1
        else:
            assert entry["votes"] == 0

    payload = {
        "votes" : [
            {
                "mensaId": "testMensa1",
                "menuId": "testMenu1",
                "voteType": "negative"
            },
            {
                "mensaId": "testMensa2",
                "menuId": "testMenu2",
                "voteType": "positive"
            },
        ],
        "update": True
    }

    resp = client.post('/api/polls/vote/'+id,  data= json.dumps(payload), content_type='application/json')

    assert resp.json["votecount"] == 1
    for entry in resp.json["options"]:
        if(entry["mensaId"] == "testMensa2"):
            assert entry["votes"] == 1
        else:
            assert entry["votes"] == 0


    payload = {
        "title": "TestVote",
        "weekday": 2,
        "mealType":"lunch",
        "options": [
            {
                "mensaId": "testMensa1", "menuId": "testMenu0"

            },
            {
                "mensaId": "testMensa22", "menuId": "testMenu21"
            }
            ]
    }

    resp = client.post('/api/polls/update/'+id,  data= json.dumps(payload), content_type='application/json')

    assert resp.status_code == 200
    assert resp.json["votecount"] == 1

    for entry in resp.json["options"]:
        assert entry["mensaId"] in ["testMensa1", "testMensa22"]
        assert entry["votes"] == 0
