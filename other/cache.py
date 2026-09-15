import threading
import time


class Cache:
    def __init__(self):
        self.__DATA = {}
        self.__clearcount = 0

    def add(self, name, value):
        self.__DATA[name] = value

    def delete(self, name):
        self.__DATA.pop(name)

    def clear(self):
        self.__DATA.clear()

    def self_clear(self, interval=60):
        while True:
            time.sleep(interval)
            self.__clearcount += 1
            print(f"[cache] auto-clear #{self.__clearcount}")
            self.clear()

    def get(self, name):
        return self.__DATA.get(name)

    def deletethathas(self, name):
        newdata = {}
        for k, v in self.__DATA.items():
            if name not in k:
                newdata[k] = v
        self.__DATA = newdata

    def check_key(self, name):
        return name in self.__DATA

    def is_empty(self, name):
        return self.__DATA[name]

    def prin(self):
        print(self.__DATA)


cache = Cache()

_cleaner = threading.Thread(target=cache.self_clear, args=(60,), daemon=True)
_cleaner.start()