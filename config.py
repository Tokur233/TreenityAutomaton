import os
from dotenv import load_dotenv

load_dotenv()

TARGET_COURSE_URL = os.getenv("TARGET_COURSE_URL", "")

DB_FILE = "answers_db.json"
STATE_FILE = "zhihuishu_state.json"
BLACKLIST_FILE = "local_blacklist.json"
EXCEPTIONS_FILE = "exceptions.json"
