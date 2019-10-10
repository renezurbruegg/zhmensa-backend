import pytest


from pymongo import MongoClient
TESTING_DATABASE = "zhmensa_testing"
TESTING_COLLECTION_PREFIX = "testing_"
MENUS = "menus"
MENSAS = "mensas"

@pytest.fixture(scope='module')
def init_database():


    db = MongoClient("localhost", 27017)[TESTING_DATABASE]




    yield db  # this is where the testing happens!

    db[TESTING_DATABASE_PREFIX + MENUS].drop()
    db[TESTING_DATABASE_PREFIX + MENSAS].drop()
