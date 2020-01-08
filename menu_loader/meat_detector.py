import pickle


class MeatDetector:

    def __init__(self):
        """ Loads pickle files into meat and vegi list"""
        with open('vegilist.pickle', 'rb') as fp:
            self.vegiList_de = pickle.load(fp)

        with open('meatlist.pickle', 'rb') as fp:
            self.meatList_de = pickle.load(fp)

        self.meatMatch = []
        self.vegiMatch = []

    def containsMeat(self, stringList):
        if stringList is None:
            return False

        wordList = []
        """ Contains all words of the string."""
        for line in stringList:
            wordList.extend(
                line.replace("  ", " ").replace(",", " ").replace("'", "").replace('"', "").replace("&",
                                                                                                    "").lower().split(
                    " "))

        v = 0
        # vegi matches
        m = 0
        # meat matches
        for word in wordList:
            if word == "":
                continue
            elif word in self.meatList_de:
                m += 1
                if word not in self.meatMatch:
                    self.meatMatch.append(word)

            elif word in self.vegiList_de:
                v += 1
                if word not in self.vegiMatch:
                    self.vegiMatch.append(word)

        # print("score: (m/v) : (" + str(m) + "/" + str(v) + ")")
        # print("deciding for: " + str(v >= m))
        return v < m

    def getMatchedMeatWords(self):
        return self.meatMatch

    def getMatchedVegiWords(self):
        return self.vegiMatch
