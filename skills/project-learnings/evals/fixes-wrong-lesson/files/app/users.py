def fetch_user(user_id: int):
    if not isinstance(user_id, int):
        raise TypeError("user_id must be an int")
    return {"id": user_id}
