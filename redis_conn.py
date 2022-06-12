import redis
from environs import Env

env = Env()
env.read_env()
REDIS_URL = env.str("REDIS_URL")
REDIS_PORT = env.str("REDIS_PORT")
REDIS_PASS = env.str("REDIS_PASS")


def get_redis(db=0):
    return redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=db, password=REDIS_PASS)


conn = get_redis()
