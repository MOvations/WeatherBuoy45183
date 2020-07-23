import pandas as pd
from bs4 import BeautifulSoup
import re
from selenium import webdriver
import chromedriver_binary
import string

pd.options.display.float_format = "{:.0f}".format

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from datetime import datetime as dt
import datetime
import time
import pytz

east = pytz.timezone("US/Eastern")

# to install ChromeDriverManager() on first use
# chrome_options = Options()
# webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

from collections import OrderedDict

Stations = OrderedDict()  # First Uppercase since this will be the master dict of dfs
stations = ["KMIGLENA6", "KMIMAPLE4", "KMIMAPLE5", "KMILELAN9", "KMIGLENA5"]


################ FUNCTIONS ############################################################


class StationReader:
    def __init__(self):
        chrome_options = Options()
        # Comment out when developing / debugging
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=800,600")
        self.driver = webdriver.Chrome(options=chrome_options)
        # self.driver.get("https://www.wunderground.com/dashboard/pws/KMIGLENA6")

    def getTableData(self, station, date):
        url = f"https://www.wunderground.com/dashboard/pws/{station}/table/{date}/{date}/daily"
        self.driver.get(url)
        time.sleep(12)
        html = self.driver.execute_script("return document.body.innerHTML;")
        # collect all the tables into dataframes
        dfs = pd.read_html(html)
        return dfs[3]


# tz aware:
# start = datetime.datetime(2020,6,28, tzinfo=east).date()
# end = dt.now(tz=east).date()

# NOT tz aware:
start = datetime.datetime(2020, 6, 28).date()
end = dt.now().date()

num_of_days = int((end - start).days)
date_list = [(start + datetime.timedelta(days=x)) for x in range(num_of_days)]

# Load the scraper bot
bot = StationReader()

for station in stations:

    # initialize the dataset
    data = bot.getTableData(station=station, date="2020-06-27")
    data.drop([0], inplace=True)
    data["Date"] = "2020-06-27"
    data["timestamp"] = pd.to_datetime(
        (data.Date.astype(str) + " " + data.Time), format="%Y-%m-%d %I:%M %p"
    )
    data.set_index("timestamp", inplace=True)
    print(data.tail())

    for d in date_list:
        # occationally personal weatherstations are down for a few days, so...
        try:
            data_temp = bot.getTableData(station=station, date=str(d))
            data_temp.drop([0], inplace=True)
            data_temp["Date"] = str(d)
            data_temp["timestamp"] = pd.to_datetime(
                (data_temp.Date.astype(str) + " " + data_temp.Time),
                format="%Y-%m-%d %I:%M %p",
            )
            data_temp.set_index("timestamp", inplace=True)
            data = pd.concat([data, data_temp])
        #     print(data.tail())
        except Exception:
            pass

    data.to_csv(f"ws_{station}_{data.index[-1].date()}.csv")
    Stations[station] = data
    data.tail()
