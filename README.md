# import-solaredge
Allows you to import data from the solar edge API if you have an API key. Since the API is limited to 300 daily requests, you may further limit the API calls made by the import.
Depending on the image used, either power (tag 'power', unit W) or energy (tag 'energy', unit Wh) values will be imported.

## Outputs
* purchased (float): barometric pressure at station height
* production (float): temperature in 2 m height
* consumption (float): temperature in 5 cm height
* self_consumption (float): relative humidity in 2 m height
* feed_in (float): dew point in 2 m height
* site (string): site id as configured

## Configs
 * SITE (string): Site id
 * API_KEY (string): API key as obtained from solaredge.
 * TIMEZONE (string): Timezone of the site (defaults to 'Europe/Berlin').
 * DAILY_LIMIT (int): Limit the daily API calls (default: 300).

