from . import db

# 全設定を辞書で取得
def get_all_settings():
    return db.get_settings()

# 単一キー取得
def get_setting(key):
    settings = db.get_settings()
    return settings.get(key)

# 単一キーをboolで取得
def get_setting_bool(key):
    v = get_setting(key)
    if v is None:
        return False
    return v.lower() in ("1", "true", "yes")

# 設定更新
def update_setting(key, value):
    existing = get_setting(key)
    if existing is None:
        raise ValueError(f"設定キーが存在しません: {key}")
    db.update_setting(key, value)
