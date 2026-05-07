import os
import json
import re
from config import DB_FILE, BLACKLIST_FILE, EXCEPTIONS_FILE


def load_json_set(filepath):
    """通用的加载 JSON 数组转 Set 函数"""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_json_set(filepath, data_set):
    """通用的保存 Set 转 JSON 数组函数"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(list(data_set), f, ensure_ascii=False, indent=2)


def load_manual_blacklist():
    return load_json_set(BLACKLIST_FILE)


def load_exceptions():
    return load_json_set(EXCEPTIONS_FILE)


def add_to_exceptions(knowledge_id):
    """将跳过的节点加入例外名单"""
    ex_set = load_exceptions()
    ex_set.add(knowledge_id)
    save_json_set(EXCEPTIONS_FILE, ex_set)


def load_answers():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_answers(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def clean_title(text):
    """专门清洗题干：去除空格、换行以及开头的题号和题型标签"""
    if not text:
        return ""
    text = text.replace("\n", "").replace(" ", "").replace("\xa0", "").strip()
    text = re.sub(r"^【.*?】", "", text)
    text = re.sub(r"^\d+[\.、]", "", text)
    text = re.sub(r"^【.*?】", "", text)
    return text


def clean_option(text):
    """专门清洗选项：去除空格，剥离可能附带的字母前缀"""
    if not text:
        return ""
    text = text.replace("\n", "").replace(" ", "").replace("\xa0", "").strip()
    text = re.sub(r"^[A-Z][\.、]", "", text)
    return text
