from environs import Env

env = Env()

env.read_env()

HASS_API_TOKEN = env('HASS_TOKEN', '')
HASS_URL = env('HASS_URL', '')
HASS_BINARY_SENSOR_NAME = env('HASS_BINARY_SENSOR_NAME', 'binary_sensor.shutdown')
HASS_STATE_SENSOR_NAME = env('HASS_STATE_SENSOR_NAME', 'sensor.shutdowns')

PARSING_URL = env('PARSING_URL', '')
PARSING_INTERVAL = env('PARSING_INTERVAL', 3600)
TIMEOUT = env.int('TIMEOUT', 60)
RETRIES = env.int('RETRIES', 3)

LOG_LEVEL = env.int('LOG_LEVEL', 20)