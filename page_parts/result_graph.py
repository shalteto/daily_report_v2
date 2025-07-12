import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
from result_sample import sample_data


def show_graph():
    st.subheader("捕獲統計")
    st.caption("捕獲数の推移をグラフで表示します。")
    st.markdown(
        """
        - グラフは、捕獲数の推移を示しています。
        - グラフの上にカーソルを合わせると、日付と捕獲数が表示されます。
        """
    )
    # df = pd.DataFrame(sample_data)
    df = pd.DataFrame(st.session_state["catch_results"])

    # 日付ごとに捕獲数を集計
    count_by_date = df.groupby("catch_date").size().reset_index(name="捕獲数")
    # 日付でソート
    count_by_date = count_by_date.sort_values("catch_date")
    # グラフ表示
    st.bar_chart(
        data=count_by_date.set_index("catch_date")["捕獲数"], use_container_width=True
    )


map_style_options = {
    "衛星写真": "mapbox://styles/mapbox/satellite-v9",
    "アウトドア": "mapbox://styles/mapbox/outdoors-v11",
    "道路地図": "mapbox://styles/mapbox/streets-v11",
    "ライト（明るい）": "mapbox://styles/mapbox/light-v10",
    "ダーク（暗い）": "mapbox://styles/mapbox/dark-v10",
}


def haversine(lat1, lon1, lat2, lon2):
    # 緯度経度から距離（メートル）を計算
    R = 6371000  # 地球半径[m]
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def cluster_points(df, threshold=50):
    # 30m以内の地点をクラスタリング
    clusters = []
    used = set()
    for idx, row in df.iterrows():
        if idx in used:
            continue
        cluster = [idx]
        lat1, lon1 = row["latitude"], row["longitude"]
        for jdx, row2 in df.iterrows():
            if jdx == idx or jdx in used:
                continue
            lat2, lon2 = row2["latitude"], row2["longitude"]
            if haversine(lat1, lon1, lat2, lon2) <= threshold:
                cluster.append(jdx)
        used.update(cluster)
        clusters.append(cluster)
    return clusters


def show_map(width=400, height=400):
    st.subheader("捕獲地点マップ")
    st.caption("捕獲地点を地図上に表示します。")

    map_style_label = st.selectbox(
        "地図のスタイルを選択してください",
        options=list(map_style_options.keys()),
        index=0,
    )
    map_style_url = map_style_options[map_style_label]
    # df = pd.DataFrame(sample_data)
    df = pd.DataFrame(st.session_state["catch_results"])
    if df.empty:
        st.warning("捕獲データがありません。")
        return

    # クラスタリング
    clusters = cluster_points(df, threshold=30)
    cluster_data = []
    for cluster in clusters:
        members = df.loc[cluster]
        count = len(members)
        # 緯度経度の平均値を代表点とする
        lat = members["latitude"].mean()
        lon = members["longitude"].mean()
        # 半径: 1個体=50, 2個体=80, 3個体=110, ...（例）
        radius = 50 + (count - 1) * 30
        cluster_data.append(
            {
                "latitude": lat,
                "longitude": lon,
                "count": count,
                "radius": radius,
                "tooltip": f"個体数: {count}\n捕獲日: {', '.join(members['catch_date'].unique())}",
            }
        )
    cluster_df = pd.DataFrame(cluster_data)

    # 色は単色（青）
    cluster_df["color"] = [[255, 0, 0, 180]] * len(cluster_df)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=cluster_df,
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_color="color",
        pickable=True,
        auto_highlight=True,
        id="result_map",
    )

    # 地図の中心・ズーム自動計算
    min_lat, max_lat = cluster_df["latitude"].min(), cluster_df["latitude"].max()
    min_lon, max_lon = cluster_df["longitude"].min(), cluster_df["longitude"].max()
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    max_diff = max(lat_diff, lon_diff)
    if max_diff < 0.005:
        zoom = 15
    elif max_diff < 0.01:
        zoom = 14
    elif max_diff < 0.02:
        zoom = 13
    elif max_diff < 0.05:
        zoom = 12
    elif max_diff < 0.1:
        zoom = 11
    else:
        zoom = 10

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
    )

    chart = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip={"text": "{tooltip}"},
    )
    st.caption("●円の大きさは捕獲個体数を表します")
    st.pydeck_chart(chart, height=height)
