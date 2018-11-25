import sqlite3

class DBHelper:
    def __init__(self, dbname="todo.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)

    def setup(self):
        stmt = "CREATE TABLE IF NOT EXISTS items (description text)"
        self.conn.execute(stmt)
        self.conn.commit()

    def add_item(self, item_text):
        stmt = "INSERT INTO items (description) VALUES (?)"
        args = (item_text, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_item(self, item_text):
        stmt = "DELETE FROM items WHERE description = (?)"
        args = (item_text, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def get_items(self):
        stmt = "SELECT description FROM items"
        return [x[0] for x in self.conn.execute(stmt)]

    import json
    import requests
    import time
    import urllib
    import configparser
    import logging
    import signal
    import sys
    import sqlite3

    TOKEN_BOTSHUN = "731945647:AAGaHzuOkqSqzQi0e1-KCWb4jiplU9NpKzY"
    OWM_KEY_BOTSHUN = "b92ad179b0b026e6e03c272c3b809560"
    POLLING_TIMEOUT_BOTSHUN = 3600

    # Lambda functions to parse updates from Telegram
    def getText(update):
        return update["message"]["text"]

    def getLocation(update):
        return update["message"]["location"]

    def getChatId(update):
        return update["message"]["chat"]["id"]

    def getUpId(update):
        return int(update["update_id"])

    def getResult(updates):
        return updates["result"]

    # # Lambda functions to parse weather responses
    def getDesc(w):
        return w["weather"][0]["description"]

    def getTemp(w):
        return w["main"]["temp"]

    def getCity(w):
        return w["name"]

    logger = logging.getLogger("BotShun")
    logger.setLevel(logging.DEBUG)

    # Cities for weather requests
    cities = ["London", "New York", "Beijing", "Mumbai", "Athens", "Berlin", "Rome", "Paris", "Shanghai", "Jakarta"]

    def sigHandler(signal, frame):
        logger.info("SIGINT received. Exiting... Bye bye")
        sys.exit(0)

    # Configure file and console logging
    def configLogging():
        # Create file logger and set level to DEBUG
        # Mode = write -> clear existing log file
        handler = logging.FileHandler("run.log", mode="w")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Create console handler and set level to INFO
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(levelname)s] - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Read settings from configuration file
    def parseConfig():
        global URL, URL_OWM, POLLING_TIMEOUT

        c = configparser.ConfigParser()
        c.read("config.ini")
        TOKEN = TOKEN_BOTSHUN
        URL = "https://api.telegram.org/bot{}/".format(TOKEN)
        OWM_KEY = OWM_KEY_BOTSHUN
        URL_OWM = "http://api.openweathermap.org/data/2.5/weather?appid={}&units=metric".format(OWM_KEY)
        POLLING_TIMEOUT = POLLING_TIMEOUT_BOTSHUN

    # Make a request to Telegram bot and get JSON response
    def makeRequest(url):
        logger.debug("URL: %s" % url)
        r = requests.get(url)
        resp = json.loads(r.content.decode("utf8"))
        return resp

    # Return all the updates with ID > offset
    # (Updates list is kept by Telegram for 24h)
    def getUpdates(offset=None):
        url = URL + "getUpdates?timeout=%s" % POLLING_TIMEOUT
        logger.info("Getting updates")
        if offset:
            url += "&offset={}".format(offset)
        js = makeRequest(url)
        return js

    # Build a one-time keyboard for on-screen options
    def buildKeyboard(items):
        keyboard = [[{"text": item}] for item in items]
        replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
        logger.debug(replyKeyboard)
        return json.dumps(replyKeyboard)

    def buildCitiesKeyboard():
        keyboard = [[{"text": c}] for c in cities]
        keyboard.append([{"text": "Share location", "request_location": True}])
        replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
        logger.debug(replyKeyboard)
        return json.dumps(replyKeyboard)

    def build_keyboard2(items):
        keyboard = [[item] for item in items]
        reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
        return json.dumps(reply_markup)

    # Query OWM for the weather for place or coords
    def getWeather(place):
        if isinstance(place, dict):  # coordinates provided
            lat, lon = place["latitude"], place["longitude"]
            url = URL_OWM + "&lat=%f&lon=%f&cnt=1" % (lat, lon)
            logger.info("Requesting weather: " + url)
            js = makeRequest(url)
            logger.debug(js)
            return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))
        else:  # place name provided
            # make req
            url = URL_OWM + "&q={}".format(place)
            logger.info("Requesting weather: " + url)
            js = makeRequest(url)
            logger.debug(js)
            return u"%s \N{DEGREE SIGN}C, %s in %s" % (getTemp(js), getDesc(js), getCity(js))

    # Send URL-encoded message to chat id
    def sendMessage(text, chatId, interface=None):
        text = text.encode('utf-8', 'strict')
        text = urllib.parse.quote_plus(text)
        url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatId)
        if interface:
            url += "&reply_markup={}".format(interface)
        requests.get(url)

    # Get the ID of the last available update
    def getLastUpdateId(updates):
        ids = []
        for update in getResult(updates):
            ids.append(getUpId(update))
        return max(ids)

    # Keep track of conversation states: 'weatherReq'
    chats = {}

    # Echo all messages back
    def handleUpdates(updates):
        for update in getResult(updates):
            chatId = getChatId(update)
            try:
                text = getText(update)
            except Exception as e:
                logger.error("No text field in update. Try to get location")
                loc = getLocation(update)
                # Was weather previously requested?
                if (chatId in chats) and (chats[chatId] == "weatherReq"):
                    logger.info("Weather requested for %s in chat id %d" % (str(loc), chatId))
                    # Send weather to chat id and clear state
                    sendMessage(getWeather(loc), chatId)
                    del chats[chatId]
                continue

            if text == "/weather":
                keyboard = buildCitiesKeyboard()
                chats[chatId] = "weatherReq"
                sendMessage("Select a city", chatId, keyboard)
            elif text == "/start":
                sendMessage("Eh you dumb ah? Read instructions la", chatId)
            # elif text == "/addcity":
            #   sendMessage("Add the city",chatId)
            # elif text.startswith("/") != True:
            #    cities.append(text)
            elif text.startswith("/"):
                sendMessage("No such command la", chatId)
                continue
            elif (text in cities) and (chatId in chats) and (chats[chatId] == "weatherReq"):
                logger.info("Weather requested for %s" % text)
                # Send weather to chat id and clear state
                sendMessage(getWeather(text), chatId)
                del chats[chatId]
            else:
                keyboard = buildKeyboard(["/weather"])
                sendMessage("Eh sia la, today weather damn hot, check the weather leh", chatId, keyboard)

    def main():
        # Set up file and console loggers
        configLogging()

        # Get tokens and keys
        parseConfig()

        # Intercept Ctrl-C SIGINT
        signal.signal(signal.SIGINT, sigHandler)

        # Main loop
        last_update_id = None
        while True:
            updates = getUpdates(last_update_id)
            if len(getResult(updates)) > 0:
                last_update_id = getLastUpdateId(updates) + 1
                handleUpdates(updates)
            time.sleep(0.5)

    if __name__ == "__main__":
        main()

