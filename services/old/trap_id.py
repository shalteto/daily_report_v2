# 罠DBから罠をカウントし、罠IDを割り振る
from azure_.cosmosdb import search_container_by_query


# def count_trap():
#     # 登録罠数をカウントする
#     database_name = "sat-db"
#     container_name = "traps"
#     query = "SELECT VALUE COUNT(1) FROM c"
#     parameters = []
#     res = search_container_by_query(
#         database_name,
#         container_name,
#         query,
#         parameters,
#     )
#     count = res[0] if res else 0
#     return count
