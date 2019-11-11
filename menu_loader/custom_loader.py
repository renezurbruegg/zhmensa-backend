from typing import List
from abc import ABC, abstractmethod


class CustomMenu:
    def __init__(self):
        self.mensa: str = ""
        self.name: str = ""
        self.id: str = ""
        self.prices: dict = {}
        self.isVegi: bool = True
        self.allergene: List[str] = []
        self.date: str = ""
        self.description: List[str] = []
        self.nutritionFacts: List[str] = []
        self.lang: str = ""
        self.link: str = None
        self.origin: str = "custom loader"
        self.mealType: str = "lunch"

    def toDict(self):
        return {
            "id": self.id,
            "mensaName": self.mensa,
            "prices": self.prices,
            "description": self.description,
            "isVegi": self.isVegi,
            "allergen": self.allergene,
            "date": str(self.date),
            "mealType": self.mealType,
            "menuName": self.name,
            "origin": self.origin,
            "nutritionFacts": self.nutritionFacts,
            "lang": self.lang,
            "link": self.link
        }


class CustomMensaEntry:
    def __init__(self):
        self.name: str = ""
        self.isOpen: bool = True
        self.category: str = ""
        self.openings: dict = None
        self.address: str = None
        self.lat: float = None
        self.lng: float = None

    def __init__(self, name, category):
        self.name: str = name
        self.isOpen: bool = True
        self.category: str = category
        self.openings: dict = None
        self.address: str = None
        self.lat: float = None
        self.lng: float = None


class CustomLoader(ABC):
    def __init__(self, baseDate, lang):
        self.baseDate = baseDate
        self.lang = lang

    @abstractmethod
    def getAvailableMensas(self) -> List[CustomMensaEntry]:
        pass

    @abstractmethod
    def getMenusForMensa(self, mensaInformation) -> List[CustomMenu]:
        pass
