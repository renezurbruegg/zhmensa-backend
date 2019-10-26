import re
from datetime import timedelta
from html.parser import HTMLParser
from typing import List

import requests

from menu_loader.custom_loader import CustomLoader, CustomMensaEntry, CustomMenu

class Loader(CustomLoader):
    """ Loads menus from eth streetfood page and parses the entries to menu objects """

    PATH = {"de": "https://ethz.ch/de/campus/erleben/gastronomie-und-einkaufen/gastronomie/street-food.html",
            "en": "https://ethz.ch/en/campus/getting-to-know/cafes-restaurants-shops/gastronomy/street-food.html"}

    class MyHTMLParser(HTMLParser):
        NAME_MAPPING = {
            "Street Food Zentrum": {"name": "Streetfood Zentrum", "category": "ETH-Zentrum", "openings": None},
            "Street Food Hönggerberg": {"name": "Streetfood Höngg", "category": "ETH-Hönggerberg", "openings": None},
            "any": {
                "name": "?",
                "category": "others",
                "openings": None
            }
        }
        MENSAS = {
            0: CustomMensaEntry("Streetfood Zentrum", "ETH-Zentrum"),
            1: CustomMensaEntry("Streetfood Höngg", "ETH-Hönggerberg")
        }

        PLACE = {
            "de": "Standort: ",
            "en": "Location: "
        }

        OFFER = {
            "de": "Angebot: ",
            "en": "Offer: "
        }

        def __init__(self, lang, basedate, startSemester, endSemester, meatDetector):
            super().__init__()
            self.textImageReached = False
            self.tableDivReached = False
            self.startParsingTableContent = False
            self.columnsInTable = 4
            self.headerColumns = 0
            self.currentColumn = 0
            self.currentRow = 0
            self.menus: List[CustomMenu] = []
            self.currentMenu : CustomMenu = None
            self.currentDay = -1
            self.lang = lang
            self.date = basedate
            self.currentMensa: CustomMensaEntry = None
            self.mensas: List[CustomMensaEntry]= []
            self.startSemester = startSemester
            self.endSemester = endSemester
            self.meatDetector = meatDetector
            self.tablecounter = 0
            self.endReached = False

        def feed(self, data):
            super().feed(data.replace("<br>", ""))
            if self.currentMenu is not None:
                self.currentMenu.isVegi = not self.meatDetector.containsMeat(self.currentMenu.description)
            self.menus = [x for x in self.menus if x.id != ""]

        def handle_starttag(self, tag, attrs):
            if self.endReached:
                return
            #print("tag: " + str(tag))
            if tag == "div":
                for type, value in attrs:
                    #print(value)
                    if type == "class" and value.strip() == "textimage":
                        #print("class reached div ")
                        #print(attrs)
                        print(self.mensas)
                        self.textImageReached = True
                        #print("ofund")
                        #print(attrs)
                        return
                    elif type == "class" and value.strip() == "table-matrix":
                        self.tableDivReached = True


                #print(attrs)
                # Skip break tagsd
                return

            elif tag == "a" and self.textImageReached and not self.startParsingTableContent:
                """for type, value in attrs:
                    if type == "name":
                        if value in self.NAME_MAPPING.keys():
                            self.currentMensa = self.NAME_MAPPING[value]
                        else:
                            self.currentMensa = self.NAME_MAPPING["any"]
                            self.currentMensa["name"] = value

                        print("-----------------------------------")
                        print(self.currentMensa)
                        self.mensas.append(self.currentMensa)
                        print("-----------------------------------")
                        self.currentDay = -1
                        self.currentRow = 0
                        self.currentColumn = 0
                        break"""

            elif tag == "table" and self.tableDivReached:
                print("found table matching stuff")
                pos = len(self.mensas)

                if pos in self.MENSAS.keys():
                    self.currentMensa = self.MENSAS[pos]
                    self.mensas.append(self.currentMensa)

                self.currentDay = -1


            elif self.tableDivReached and tag == "td":
                # print("td")
                self.startParsingTableContent = True
                self.currentColumn += 1

            elif self.tableDivReached and tag == "tr":
                # print("tr")
                self.startParsingTableContent = False
                self.currentRow += 1

                if self.currentMenu is not None:
                    self.currentMenu.isVegi = not self.meatDetector.containsMeat(self.currentMenu.description)

                self.currentMenu = CustomMenu()
                self.currentMenu.lang = self.lang

                if self.currentMensa is not None:
                    self.currentMenu.mensa = self.currentMensa.name

                self.menus.append(self.currentMenu)
                self.currentColumn = 0

            elif self.startParsingTableContent and tag == "a" and self.currentMenu is not None and self.currentColumn == 2:
                #print("found a tag")
                #print(attrs)
                for type, value in attrs:
                    if type == "href":
                        self.currentMenu.link = value
                        return

        def handle_endtag(self, tag):
            if self.endReached:
                return

            if tag == "div":
                self.textImageReached = False
                return
            if tag =="td":
                self.startParsingTableContent = False

            if tag =="table"and len(self.mensas) >= 2:

                self.endReached = True

        def handle_data(self, data):
            if self.endReached:
                return

            if self.startParsingTableContent and data.strip() != "":
                if self.currentColumn == 1:
                    self.currentDay += 1

                if self.currentMenu is not None:
                    if self.currentColumn == 2:
                        # print("got anbieter: " + str(data.strip()))
                        self.currentMenu.name = data.strip()
                        self.currentMenu.id = data.strip()
                        self.currentMenu.date = str(self.date + timedelta(days=self.currentDay))

                    if self.currentColumn == 3:
                        # print("got angebot: " + str(data.strip()))
                        self.currentMenu.description.append(self.OFFER[self.lang] + data.strip())
                    if self.currentColumn == 4:
                        dataStr = data.replace("\n", "").strip()
                        location = self.parse_location(dataStr)

                        if location is None:
                            # Current day is not inside timespan
                            print("Found entry that does not match current day")
                            print(dataStr)
                            self.menus.remove(self.currentMenu)
                            return
                        # print("Got Place: " + str(location))
                        self.currentMenu.description.append(self.PLACE[self.lang] + location)

        def parse_location(self, location):
            """ Parses a given Location. e.g (Polyterasse 18.2 - 19.5) to "Polyterasse". If the current date is not
            inside the given timespan, this function returns None """
            print(location)
            location = location.replace("("," ").replace(")"," ")
            # Matches dates like 1.12, 22.1, 21.11
            datePattern = "(\\d\\d?\\.\\d\\d?)"
            fromToPattern = datePattern + "[^\\d]*-[^\\d]*" + datePattern + "[^\\d]*"
            fromTo = re.search(fromToPattern, location)

            start = self.startSemester
            end = self.endSemester

            if fromTo is not None:
                start = fromTo.group(1)
                end = fromTo.group(2)
                location = re.sub(fromToPattern + "[^\\d]+", "", location)
            else:
                match = re.search(datePattern, location)
                if match is None:
                    return location

                startStrings = ["from", "ab", "after"]
                endStrings = ["bis", "to", "until"]

                matchedStr = match.group(1)

                words = location.replace("("," ").split(" ")
                foundWord = False
                for startWord in startStrings:
                    if startWord in words:
                        location = location.replace(startWord, "")
                        foundWord = True
                        start = matchedStr

                if not foundWord:
                    for endWord in endStrings:
                        if endWord in words:
                            foundWord = True
                            location = location.replace(endWord,"")
                            end = matchedStr

                if not foundWord:
                    print("no word match for string " + str(location))
                    return None

                location = re.sub(datePattern + "[^\\d]+", "", location)

            # Check if today is in valid date range.
            comparableStartString = ""
            comparableEndString = ""

            for number in start.split("."):
                if len(number) < 2:
                    number = "0"+number
                comparableStartString = "-" + number + comparableStartString
            comparableStartString = str(self.date.year) + comparableStartString

            for number in end.split("."):
                if len(number) < 2:
                    number = "0"+number
                comparableEndString = "-" + number + comparableEndString
            comparableEndString = str(self.date.year) + comparableEndString

            isEntryValid = comparableStartString <= str(self.date + timedelta(days= self.currentDay)) <= comparableEndString

            if isEntryValid:
                location = location.replace("  ", " ").strip()
                return location

            return None

    def getAvailableMensas(self) -> List[CustomMensaEntry]:
        return self.parser.mensas


    def getMenusForMensa(self, mensaEntry: CustomMensaEntry) -> List[CustomMenu]:
        mensaName = mensaEntry.name
        list = []
        for menu in self.parser.menus:
            if menu.mensa == mensaName:
                menu.origin = "ETH-Streetfood"
                menu.id = "mensa:" + mensaName + ",Menu:" + menu.name
                list.append(menu.toDict())
        return list

    def __init__(self, lang, basedate, meatDetector):
        headers = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Cache-Control': 'no-cache',
            'Host': 'ethz.ch',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        req = requests.get(
            url=self.PATH[lang],
            params=None, headers=headers)

        self.parser = self.MyHTMLParser(lang, basedate, "16.09", "20.12", meatDetector)
        self.parser.feed(req.text)
