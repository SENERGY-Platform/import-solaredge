import sched
import unittest
from unittest import mock

import requests

from lib.site import SiteImport as site_import_module
from lib.site.SiteImport import SiteImport

API_KEY = "TESTKEY0123456789"


class SiteImportLoggingTest(unittest.TestCase):
    def setUp(self):
        config = {"API_KEY": API_KEY, "SITE": "123"}
        lib = mock.Mock()
        lib.get_config.side_effect = lambda key, default=None: config.get(key, default)
        lib.get_last_published_datetime.return_value = (None, None)
        self.scheduler = mock.Mock(spec=sched.scheduler)
        self.site_import = SiteImport(lib, self.scheduler)

    def test_api_key_not_logged_on_connection_error(self):
        url = f"https://monitoringapi.solaredge.com/site/123/energyDetails.json?startTime=x&api_key={API_KEY}"
        error = requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool(host='monitoringapi.solaredge.com', port=443): Max retries exceeded with url: {url}")
        with mock.patch.object(site_import_module.requests, "get", side_effect=error):
            with self.assertLogs(site_import_module.logger, level="ERROR") as logs:
                self.site_import._SiteImport__import()
        output = "\n".join(logs.output)
        self.assertIn("Could not get data", output)
        self.assertNotIn(API_KEY, output)


class SiteImportExtractTest(unittest.TestCase):
    def setUp(self):
        config = {"API_KEY": "key", "SITE": "123"}
        lib = mock.Mock()
        lib.get_config.side_effect = lambda key, default=None: config.get(key, default)
        lib.get_last_published_datetime.return_value = (None, None)
        self.site_import = SiteImport(lib, mock.Mock(spec=sched.scheduler))

    @staticmethod
    def __meter(meter_type, values):
        return {"type": meter_type, "values": [
            {"date": date} if value is None else {"date": date, "value": value}
            for date, value in values]}

    def test_self_consumption_is_extracted(self):
        dates = ["2026-10-15 12:00:00", "2026-10-15 12:15:00"]
        raw = {"energyDetails": {"timeUnit": "QUARTER_OF_AN_HOUR", "unit": "Wh", "meters": [
            self.__meter("Production", [(dates[0], 410.5), (dates[1], 398.0)]),
            self.__meter("Consumption", [(dates[0], 120.0), (dates[1], 135.25)]),
            self.__meter("SelfConsumption", [(dates[0], 110.0), (dates[1], None)]),
            self.__meter("FeedIn", [(dates[0], 300.5), (dates[1], 398.0)]),
            self.__meter("Purchased", [(dates[0], 10.0), (dates[1], 0.0)]),
        ]}}
        points = self.site_import._SiteImport__extract(raw)
        self.assertEqual(2, len(points))
        self.assertEqual(110.0, points[0][1]["self_consumption"])
        # A data point without a value stays None instead of failing the import.
        self.assertIsNone(points[1][1]["self_consumption"])
        self.assertEqual(135.25, points[1][1]["consumption"])


if __name__ == "__main__":
    unittest.main()
