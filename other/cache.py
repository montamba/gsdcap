DATA = {}


def inCahce(name):
    return name in DATA

def addCache(key, value):
    DATA[key] = value
    
def removeCache(key):
    DATA.pop(key)
    
def clearCache():
    DATA.clear
        


