import threading
import time

class Cache:
    def __init__(self):
        self.__DATA = {}
        threading.Thread(target=self.self_clear).start()
        
        
        
    def add(self,name,value):
        self.__DATA[name] = value
    
    def delete(self,name):
        self.__DATA.pop(name)
        
    def clear(self):
        self.__DATA.clear() 
        
    def self_clear(self):
        while True:
            time.sleep(100)
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





