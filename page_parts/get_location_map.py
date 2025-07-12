import streamlit as st
import pydeck as pdk
import pandas as pd
from services.gps import get_location


def location_map(width=400, height=300):
    get_location()
    location = st.text_input(
        "上のテキストをコピペ入力してください", value=st.session_state.location
    )
    if location:
        st.session_state.location = location

    if "location" not in st.session_state or not st.session_state.location:
        st.warning("座標データがありません。")
        return

    # データをデータフレームに変換
    lat, lon = map(float, st.session_state.location.split(","))
    location_data = pd.DataFrame({"latitude": [lat], "longitude": [lon]})

    # 緯度と経度を10mずつ移動させるボタン
    tani = int(st.text_input("移動距離", value="100"))
    lamda = tani / 100000
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(f"北 {tani}m"):
            lat += lamda
        if st.button(f"南 {tani}m"):
            lat -= lamda
    with col2:
        if st.button(f"東 {tani}m"):
            lon += lamda
        if st.button(f"西 {tani}m"):
            lon -= lamda

    # 更新された座標を小数点以下4桁に四捨五入して保存
    lat = round(lat, 4)
    lon = round(lon, 4)
    st.session_state.location = f"{lat},{lon}"
    location_data = pd.DataFrame({"latitude": [lat], "longitude": [lon]})

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=location_data,
        get_position="[longitude, latitude]",
        get_radius=50,
        get_color=[0, 0, 255, 160],
        pickable=True,
        auto_highlight=True,
        id="map",
    )

    # 初期表示の設定
    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=12,
    )

    # Pydeckチャートを表示
    chart = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",
        tooltip={"現在位置"},
    )

    st.pydeck_chart(chart, width=width, height=height)
