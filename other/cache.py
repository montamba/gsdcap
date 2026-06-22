import threading
import time

class Cache:
    def __init__(self):
        self.__DATA = {}
        self.__clearcount = 0
        threading.Thread(target=self.self_clear).start()
        
        
        
    def add(self,name,value):
        self.__DATA[name] = value
    
    def delete(self,name):
        self.__DATA.pop(name)
        
    def clear(self):
        self.__DATA.clear() 
        
    def self_clear(self):
        print("start")
        while True:
            time.sleep(10)
            print("clearing cache +", self.__clearcount)
            self.__clearcount += 1
            self.clear()
            
               
        
    def get(self, name):
        return self.__DATA[name] 
    
    def deletethathas(self,name):
        newdata = {}
        for k,v in self.__DATA.items():
            if name not in k:
                newdata[k] = v
        self.__DATA = newdata
        
    def check_key(self, name):
        return name in self.__DATA 
    
    
    def prin(self):
        print(self.__DATA)

cache = Cache()






