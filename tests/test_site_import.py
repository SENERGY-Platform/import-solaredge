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


if __name__ == "__main__":
    unittest.main()
