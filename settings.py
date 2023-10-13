from environs import Env

env = Env()

env.read_env()

PARSING_URL = env('PARSING_URL', '')
PARSING_INTERVAL = env('PARSING_INTERVAL', 3600)
TIMEOUT = env.int('TIMEOUT', 60)
RETRIES = env.int('RETRIES', 3)

LOG_LEVEL = env.int('LOG_LEVEL', 20)
