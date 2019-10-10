import sys, os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

import pytest

from pymongo import MongoClient


import menuCrawler as crawler
from rssMenuPlanDict import VALID_RSS_MENU_ENTRIES

TESTING_DATABASE = "zhmensa_testing"
TESTING_COLLECTION_PREFIX = "testing_"
MENUS = "menus"
MENSAS = "mensas"



@pytest.fixture(scope='module')
def init_database():


    db = MongoClient("localhost", 27017)[TESTING_DATABASE]




    yield db  # this is where the testing happens!

    db[TESTING_COLLECTION_PREFIX + MENUS].drop()
    db[TESTING_COLLECTION_PREFIX + MENSAS].drop()


def test_read_menu_uzh(init_database):
    db = init_database;

    UZH_CONNECTION_INFO = {
        "id": 146,
        "mensa": "Tierspital",
        "mealType": "lunch",
        "category": "UZH-Irchel",
        "meal_openings": None,
        "opening": None
      }

    crawler.loadUZHMensaForUrl(UZH_CONNECTION_INFO, "./tests/rssMenuPlan.html", db, "de", "2019-10-10")

    for entry in VALID_RSS_MENU_ENTRIES:
        record  = db[MENUS].find(entry)
        assert record != None
        
    db[MENUS].drop()
