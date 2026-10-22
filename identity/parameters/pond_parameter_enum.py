from enum import Enum

class PondParameters(Enum) :
    DO = ("DO","mg/L")
    pH = ("pH","")
    tem = ("Temperature","C")
    NH3 = ("NH3","mg/L")
    NO2_N = ("NO2-_N","mg/L")
    salinity = ("salinity","ppt")

    def __init__(self, label : str, unit : str):
        self.label = label
        self.unit = unit


