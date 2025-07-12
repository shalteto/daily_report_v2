import streamlit as st
import time


def get_all_data_test(use_cross_partition=True):
    client = st.session_state["cosmos_client"]
    fy_value = "2025年"
    exclude_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}

    start_time = time.perf_counter()

    if use_cross_partition:
        query = """
        SELECT * FROM c
        WHERE (
            c.category = 'user'
            OR (
                c.category IN ('trap', 'daily', 'result')
                AND IS_DEFINED(c.fy)
                AND c.fy = @fy
            )
        )
        """
        parameters = [{"name": "@fy", "value": fy_value}]
        data = client.search_container_by_query(query, parameters)

    else:
        # パーティション別に個別クエリ
        categories_with_fy = ["trap", "daily", "result"]
        query = """
        SELECT * FROM c
        WHERE IS_DEFINED(c.fy) AND c.fy = @fy
        """
        parameters = [{"name": "@fy", "value": fy_value}]
        data = []

        for category in categories_with_fy:
            part_data = client.search_container_by_query(query, parameters)
            data.extend(part_data)

        # userカテゴリは全件取得
        user_query = "SELECT * FROM c"
        user_data = client.search_container_by_query(user_query, [])
        data.extend(user_data)

    end_time = time.perf_counter()
    duration = end_time - start_time

    # データ整形
    users = []
    traps = []
    daily_reports = []
    catch_results = []

    for item in data:
        filtered_item = {k: v for k, v in item.items() if k not in exclude_fields}
        category = filtered_item.get("category")
        if category == "user":
            users.append(filtered_item)
        elif category == "trap":
            traps.append(filtered_item)
        elif category == "daily":
            daily_reports.append(filtered_item)
        elif category == "result":
            catch_results.append(filtered_item)

    return {
        "users": users,
        "traps": traps,
        "daily_reports": daily_reports,
        "catch_results": catch_results,
        "duration_sec": round(duration, 3),
        "mode": "cross-partition" if use_cross_partition else "partitioned",
    }


def get_all_data():
    start_time = time.perf_counter()
    client = st.session_state["cosmos_client"]
    fy_value = "2025年度"
    query = """
    SELECT * FROM c
    WHERE (
        c.category IN ('user', 'order')
        OR (
            c.category IN ('trap', 'daily', 'result')
            AND IS_DEFINED(c.fy)
            AND c.fy = @fy
        )
    )
    """
    parameters = [{"name": "@fy", "value": fy_value}]
    data = client.search_container_by_query(query, parameters)
    end_time = time.perf_counter()
    duration = end_time - start_time
    st.write(f"データ取得時間: {duration:.3f}秒")
    # 除外するフィールド
    exclude_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}

    users = []
    traps = []
    daily_reports = []
    catch_results = []
    orders = []

    for item in data:
        # 除外フィールドを削除
        filtered_item = {k: v for k, v in item.items() if k not in exclude_fields}
        if filtered_item["category"] == "user":
            users.append(filtered_item)
        elif filtered_item["category"] == "trap":
            traps.append(filtered_item)
        elif filtered_item["category"] == "daily":
            daily_reports.append(filtered_item)
        elif filtered_item["category"] == "result":
            catch_results.append(filtered_item)
        elif filtered_item["category"] == "order":
            orders.append(filtered_item)

    return {
        "users": users,
        "traps": traps,
        "daily_reports": daily_reports,
        "catch_results": catch_results,
        "orders": orders,
    }


if __name__ == "__main__":
    data = get_all_data()
    print(data)
