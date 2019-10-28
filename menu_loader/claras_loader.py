from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import List

import requests

from menu_loader.custom_loader import CustomLoader, CustomMenu, CustomMensaEntry


class MyHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.div_counter = 0
        self.postFound = False
        self.postString = ""
        self.postDate = None
        self.posts = {}
        self.postsContent = []
        self.postContentFound = False

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for type, value in attrs:
                if type == "class" and "userContentWrapper" in value:
                    self.postFound = True
                    return
                if type == "class" and " userContent " in value:
                    self.postContentFound = True
                    return
            if self.postFound:
                self.div_counter += 1


        if tag == "abbr" and self.postFound:
            for type, value in attrs:
                if type == "title":
                    dateStr = value.split(",")[0]
                    hourStr = value.split(",")[1].strip()
                    startTimeDate = datetime.strptime(dateStr, '%d.%m.%y').date()
                    # Somehow Facebook time is wrong. if post was posted really late (e.g. 23.20) we need to add a day
                    if hourStr > "04:00":
                        startTimeDate = startTimeDate + timedelta(days= 1)
                    self.postDate = str(startTimeDate)
                    return

    def handle_endtag(self, tag):
        if tag == "div" and self.postFound:
            self.div_counter -= 1

            if self.div_counter == 0:
                self.postFound = False
                self.postContentFound = False
                if "geteilt." not in self.postString:
                    self.postString = self.postString.replace("....", "...")
                    self.postsContent.append(self.postString)
                    if self.postDate is not None:
                        self.posts[self.postDate] = self.postString
                self.postString = ""

        elif self.postContentFound and tag == "p" and self.postString != "":
            self.postString = self.postString + "\n"

    def handle_data(self, data):
        if self.postContentFound:
            self.postString = self.postString + " " + data


class Loader(CustomLoader):

    def __init__(self, baseDate, lang):
        super().__init__(baseDate, lang)
        self.baseDate = baseDate
        self.lang = lang
        self.path = "https://www.facebook.com/pg/klaraskitchen/posts/"

        headers = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Cache-Control': 'no-cache',
            'Referer': 'https://www.facebook.com/pg/klaraskitchen/posts/',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        req = requests.get(url=self.path, params=None, headers=headers)
        self.parser = MyHTMLParser()
        self.parser.feed(req.text)

    def getAvailableMensas(self) -> List[CustomMensaEntry]:
        entry = CustomMensaEntry("Klaras Kitchen", 'others')
        return [entry]

    def getMenusForMensa(self, mensaInformation) -> List[CustomMenu]:
        if mensaInformation.name == "Klaras Kitchen":
            retList = []
            for day in range(5):
                retList.extend(self.getMenusForDay(str(self.baseDate + timedelta(days= day))))
            return retList
        return []

    def getMenusForDay(self, day) -> List[CustomMenu]:
        if day in self.parser.posts.keys():
            description = self.parser.posts[day].split("\n")
        elif self.lang == "de":
            description = ["Momentan noch kein Menü verfügbar---Menüs werden gewöhnlich um ca. 09.00 Uhr publiziert."]
        else:
            description = ["Currently no menu available---Menus are normally published around 09.00."]

        retList = []
        for line in description:
            if line.strip() == "":
                continue
            menu = CustomMenu()
            menu.mensa = "Klaras Kitchen"
            menu.name = "Tagesmenüs" if self.lang == "de" else "Daily Menus"
            menu.lang = self.lang
            menu.link = self.path
            menu.origin = "Klaras-loader"
            menu.id = "KlarasKitchen-Dayli-Menu" + str(len(retList))
            menu.date = str(day)
            menu.description = line.replace("...", "--- ---").split("---")
            retList.append(menu)

        return retList

    def hasMenuForDay(self, date):
        return str(date) in self.parser.posts.keys()

