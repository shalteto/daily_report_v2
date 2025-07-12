import streamlit as st
import pydeck as pdk
import pandas as pd


def sample_trap_data():
    trap_data = [
        {
            "latitude": 34.600521,
            "longitude": 137.121363,
            "trap_name": "花の村ソーラーの道",
            "status": "稼働中",
            "id": "Trap-001",
        },
        {
            "latitude": 34.606175,
            "longitude": 137.109573,
            "trap_name": "ハラサワ",
            "status": "稼働中",
            "id": "Trap-002",
        },
        {
            "latitude": 34.610929,
            "longitude": 137.113483,
            "trap_name": "アキモトさんの檻",
            "status": "停止中",
            "id": "Trap-003",
        },
        {
            "latitude": 34.596175,
            "longitude": 137.123857,
            "trap_name": "花の村駐車場横",
            "status": "稼働中",
            "id": "Trap-004",
        },
        {
            "latitude": 34.597054,
            "longitude": 137.126528,
            "trap_name": "花の村の奥",
            "status": "撤去済み",
            "id": "Trap-005",
        },
    ]
    return trap_data


def call_trap_date():
    return st.session_state["traps"]


map_style_options = {
    "衛星写真": "mapbox://styles/mapbox/satellite-v9",
    "アウトドア": "mapbox://styles/mapbox/outdoors-v11",
    "道路地図": "mapbox://styles/mapbox/streets-v11",
    "ライト（明るい）": "mapbox://styles/mapbox/light-v10",
    "ダーク（暗い）": "mapbox://styles/mapbox/dark-v10",
}


def trap_map(width=400, height=400, mode="稼働中", multi_select="multi-object"):
    trap_data = st.session_state.traps
    # trap_data = sample_trap_data()

    if not trap_data:
        st.warning("トラップデータがありません。")
        return
    map_style_label = st.selectbox(
        "地図のスタイルを選択してください",
        options=list(map_style_options.keys()),
        index=0,
    )
    map_style_url = map_style_options[map_style_label]
    # データをデータフレームに変換
    trap_data = pd.DataFrame(trap_data)

    # モードに基づいてデータをフィルタリング
    if mode != "すべて":
        trap_data = trap_data[trap_data["status"] == mode]

    # カラーの設定（事前にデータフレームへカラム追加）
    trap_data["color"] = [[0, 255, 0]] * len(trap_data)  # デフォルトカラー（緑色）
    for idx, row in trap_data.iterrows():
        if row["status"] == "稼働中":
            trap_data.at[idx, "color"] = [255, 216, 0, 160]  # 黄色
        elif row["status"] == "撤去済み":
            trap_data.at[idx, "color"] = [225, 0, 0, 160]  # 赤色

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=trap_data,
        get_position="[longitude, latitude]",
        get_radius=50,
        get_color="color",
        pickable=True,
        auto_highlight=True,
        id="map",
    )

    # trap_dataの全座標が表示されるように中心座標とズームを自動計算
    if not trap_data.empty:
        min_lat, max_lat = trap_data["latitude"].min(), trap_data["latitude"].max()
        min_lon, max_lon = trap_data["longitude"].min(), trap_data["longitude"].max()
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # 距離に応じてズームレベルを調整（簡易計算）
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        max_diff = max(lat_diff, lon_diff)
        adust_diff = 1.2  # 緯度1度あたりの距離（メートル）
        # データが近いほどズームイン、遠いほどズームアウト
        if max_diff < 0.005:
            zoom = 15 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
        elif max_diff < 0.01:
            zoom = 14 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
        elif max_diff < 0.02:
            zoom = 13 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
        elif max_diff < 0.05:
            zoom = 12 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
        elif max_diff < 0.1:
            zoom = 11 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
        else:
            zoom = 10 + adust_diff
            print(f"zoom: {zoom} (max_diff: {max_diff})")
    else:
        center_lat = 34.614375
        center_lon = 137.144072
        zoom = 12

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
    )

    # Pydeckチャートを表示
    chart = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip={"text": "{trap_name}"},
    )
    if mode != "稼働中":
        st.caption("🟡稼働中  🔴撤去済み")
    event = st.pydeck_chart(
        chart,
        selection_mode=multi_select,  # single-objectにするときは,
        on_select="rerun",
        # width=width,
        height=height,
    )
    if event.selection["objects"] == {}:
        st.session_state.selected_objects = {"map": []}
    else:
        st.session_state.selected_objects = event.selection["objects"]
    # print("event.selection==>")
    # print(event.selection)
    # print("st.session_state.selected_objects==>")
    # print(st.session_state.selected_objects)
    if st.session_state.selected_objects:
        for p in st.session_state.selected_objects["map"]:
            print(p["trap_name"])
