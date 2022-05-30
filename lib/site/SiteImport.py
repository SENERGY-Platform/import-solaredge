#  Copyright 2022 InfAI (CC SES)
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import datetime
import os
import sched
import typing

import requests

from import_lib.import_lib import ImportLib, get_logger

from lib.site import Point

logger = get_logger(__name__)
baseUrl = 'https://monitoringapi.solaredge.com/site/'
dtFormat = '%Y-%m-%d %H:%M:%S'


class SiteImport:
    def __init__(self, lib: ImportLib, scheduler: sched.scheduler):
        self.__lib = lib
        self.__scheduler = scheduler

        self.__api_key = self.__lib.get_config("API_KEY", None)
        if self.__api_key is None or len(self.__api_key) == 0:
            raise AssertionError("API_KEY not set")
        self.__site = self.__lib.get_config("SITE", None)
        if self.__site is None or len(self.__site) == 0:
            raise AssertionError("SITE not set")
        import pytz
        self.__timezone = pytz.timezone(self.__lib.get_config("TIMEZONE", 'Europe/Berlin'))

        self.__delay = (60 * 60 * 24) / self.__lib.get_config("DAILY_LIMIT", 300)

        self.__mode = os.getenv("TAG", "energy").lower()
        self.__last_dt, _ = self.__lib.get_last_published_datetime()
        self.__scheduler.enter(0, 1, self.__import)

    def __import(self):
        if self.__last_dt is None:
            start_time_f = (datetime.datetime.now() - datetime.timedelta(days=30)).astimezone(self.__timezone).strftime(
                dtFormat)
        else:
            start_time_f = (self.__last_dt + datetime.timedelta(minutes=1)).strftime(dtFormat)
        end_time = datetime.datetime.now()
        end_time_f = end_time.astimezone(self.__timezone).strftime(dtFormat)

        try:
            resp = requests.get(
                f"{baseUrl}{self.__site}/{self.__mode}Details.json?startTime={start_time_f}&endTime={end_time_f}&api_key={self.__api_key}&timeUnit=QUARTER_OF_AN_HOUR")
            if not resp.ok:
                raise Exception("Request got unexpected status code " + str(resp.status_code))
            resp = resp.json()
            points = self.__extract(resp)
            for dt, val in points:
                self.__lib.put(dt, val)
            logger.info(f"Imported {len(points)} most recent data points")
            self.__last_dt = points[len(points) - 1][0]

        except Exception as e:
            logger.error(f"Could not get data {e}")
            return
        finally:
            self.__scheduler.enter(self.__delay, 1, self.__import)

    def __extract(self, raw: typing.Dict) -> typing.List[typing.Tuple[datetime.datetime, typing.Dict]]:
        resp = []

        purchased = []
        production = []
        consumption = []
        self_consumption = []
        feed_in = []
        for meter in raw[f"{self.__mode}Details"]["meters"]:
            if meter["type"] == "Purchased":
                purchased = meter["values"]
            elif meter["type"] == "Production":
                production = meter["values"]
            elif meter["type"] == "Consumption":
                consumption = meter["values"]
            elif meter["type"] == "SelfConsumption":
                self_consumption = meter["values"]
            elif meter["type"] == "FeedIn":
                feed_in = meter["values"]
        if len(purchased) != len(production) or len(purchased) != len(consumption) or len(purchased) != len(
                self_consumption) or len(purchased) != len(feed_in):
            raise Exception("Unexpected API response format")
        for i in range(len(purchased)):
            ts = purchased[i]["date"]
            if ts != production[i]["date"] or ts != consumption[i]["date"] or ts != self_consumption[i]["date"] or ts != \
                    feed_in[i]["date"]:
                raise Exception("Unexpected API response format")
            ts = self.__timezone.localize(datetime.datetime.strptime(ts, dtFormat))
            purchased_i = purchased[i]["value"] if "value" in purchased[i] else None
            production_i = production[i]["value"] if "value" in production[i] else None
            self_consumption_i = self_consumption[i]["value"] if "value" in self_consumption else None
            feed_in_i = feed_in[i]["value"] if "value" in feed_in[i] else None
            consumption_i = consumption[i]["value"] if "value" in consumption[i] else None

            if purchased_i is not None \
                    or production_i is not None \
                    or self_consumption_i is not None \
                    or feed_in_i is not None \
                    or consumption_i is not None:
                resp.append((ts, Point.get_message(purchased=purchased_i, production=production_i,
                                                   self_consumption=self_consumption_i,
                                                   feed_in=feed_in_i, consumption=consumption_i, site=self.__site)))

        return resp
