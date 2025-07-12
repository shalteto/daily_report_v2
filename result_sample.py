sample_data = [
    {
        "id": "e54f9936-759c-4fcd-9bdd-7114c41a87d7",
        "category": "result",
        "fy": "2025年度",
        "result_id": "SS-1",
        "users": ["鈴木翔一郎", "伊藤淳", "宮田清一"],
        "catch_date": "2025-05-02",
        "catch_method": "くくり罠",
        "trap": "",
        "latitude": 34.600521,
        "longitude": 137.121363,
        "sex": "メス",
        "adult": "成獣",
        "size": 88,
        "disposal": "埋設",
        "comment": "テスト",
    },
    {
        "id": "6a3145f1-e37c-45c4-8bc8-35abd3161eab",
        "category": "result",
        "fy": "2025年度",
        "result_id": "SS-1",
        "users": ["鈴木翔一郎", "大久保健二"],
        "catch_date": "2025-05-06",
        "catch_method": "くくり罠",
        "trap": "",
        "latitude": 34.643,
        "longitude": 137.1814,
        "sex": "オス",
        "adult": "成獣",
        "size": 100,
        "disposal": "焼却",
        "comment": "",
    },
    {
        "id": "f1b7c51e-1d1e-42aa-8791-496fe179e09f",
        "category": "result",
        "fy": "2025年度",
        "result_id": "SS-1",
        "users": ["鈴木翔一郎"],
        "catch_date": "2025-05-06",
        "catch_method": "箱罠",
        "trap": "",
        "latitude": 34.600521,
        "longitude": 137.121363,
        "sex": "メス",
        "adult": "幼獣",
        "size": 50,
        "disposal": "焼却",
        "comment": "",
    },
    {
        "id": "a97eabdd-7a4b-49fe-b8b6-5d14918dbda1",
        "category": "result",
        "fy": "2025年度",
        "result_id": "SS-1",
        "users": ["鈴木翔一郎"],
        "catch_date": "2025-05-06",
        "catch_method": "くくり罠",
        "trap": "",
        "latitude": 34.643,
        "longitude": 137.1814,
        "sex": "メス",
        "adult": "幼獣",
        "size": 100,
        "disposal": "焼却",
        "comment": "",
    },
]
import random
import uuid
import datetime
import math


def random_nearby_coord(lat, lon, max_dist_m=1000):
    # 1度あたりの緯度は約111,000m
    delta_deg = max_dist_m / 111000
    dlat = random.uniform(-delta_deg, delta_deg)
    # 経度は緯度によって変わる
    dlon = random.uniform(-delta_deg, delta_deg) / abs(math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


base_points = [(34.600521, 137.121363), (34.643, 137.1814)]
users_list = [
    ["鈴木翔一郎", "伊藤淳", "宮田清一"],
    ["鈴木翔一郎", "大久保健二"],
    ["鈴木翔一郎"],
    ["鈴木翔一郎", "伊藤淳"],
    ["鈴木翔一郎", "大久保健二", "宮田清一"],
]
catch_methods = ["くくり罠", "箱罠"]
sexes = ["オス", "メス"]
adults = ["成獣", "幼獣"]
disposals = ["埋設", "焼却"]
comments = ["", "テスト", "追加データ", "確認用"]
sizes = [50, 88, 100, 75, 60, 95]

for i in range(20):
    base_lat, base_lon = random.choice(base_points)
    lat, lon = random_nearby_coord(base_lat, base_lon)
    sample_data.append(
        {
            "id": str(uuid.uuid4()),
            "category": "result",
            "fy": "2025年度",
            "result_id": f"SS-{random.randint(2, 10)}",
            "users": random.choice(users_list),
            "catch_date": f"2025-05-{random.randint(2, 20):02d}",
            "catch_method": random.choice(catch_methods),
            "trap": "",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "sex": random.choice(sexes),
            "adult": random.choice(adults),
            "size": random.choice(sizes),
            "disposal": random.choice(disposals),
            "comment": random.choice(comments),
        }
    )
