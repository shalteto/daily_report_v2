import streamlit as st
import pandas as pd
import pydeck as pdk
from PIL import Image
import piexif
import io
import math
import uuid
from azure_.cosmosdb import CosmosDBClient


# --- GPS座標抽出 ---
def get_gps_coordinates(file_data):
    img = Image.open(io.BytesIO(file_data))
    exif_data = img.info.get("exif")
    if not exif_data:
        return None
    exif_dict = piexif.load(exif_data)
    gps_info = exif_dict.get("GPS", {})
    if not gps_info:
        return None

    def convert_to_degrees(value):
        d, m, s = value
        return d[0] / d[1] + (m[0] / m[1]) / 60 + (s[0] / s[1]) / 3600

    try:
        lat = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLatitude])
        lon = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLongitude])
        if gps_info[piexif.GPSIFD.GPSLatitudeRef] != b"N":
            lat = -lat
        if gps_info[piexif.GPSIFD.GPSLongitudeRef] != b"E":
            lon = -lon
        return lat, lon
    except Exception:
        return None


# --- 2点間距離（m） ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半径[m]
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# --- 地図表示 ---
def show_map(trap_points):
    if not trap_points or not isinstance(trap_points, list):
        st.warning("座標データがありません。")
        return
    # latitude/longitudeカラムがあるものだけ抽出
    filtered = [r for r in trap_points if "latitude" in r and "longitude" in r]
    if not filtered:
        st.warning("有効な座標データがありません。")
        return
    df = pd.DataFrame(filtered)
    map_style_options = {
        "衛星写真": "mapbox://styles/mapbox/satellite-v9",
        "アウトドア": "mapbox://styles/mapbox/outdoors-v11",
        "道路地図": "mapbox://styles/mapbox/streets-v11",
        "ライト（明るい）": "mapbox://styles/mapbox/light-v10",
        "ダーク（暗い）": "mapbox://styles/mapbox/dark-v10",
    }
    map_style_label = st.selectbox(
        "地図のスタイルを選択してください", list(map_style_options.keys()), index=0
    )
    map_style_url = map_style_options[map_style_label]
    df["color"] = [[0, 255, 0, 160]] * len(df)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_radius=50,
        get_color="color",
        pickable=True,
        auto_highlight=True,
        id="map",
    )
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=14)
    chart = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip={"text": "{name}"},
    )
    st.pydeck_chart(chart, height=400)


# --- Streamlit UI ---
def main():
    st.subheader("わな設置調査 - 座標登録＆地図表示")
    # CosmosDBクライアント
    if "cosmos_client_traps" not in st.session_state:
        st.session_state["cosmos_client_traps"] = CosmosDBClient(container_name="traps")
    client = st.session_state["cosmos_client_traps"]

    # 既存座標データ取得
    query = "SELECT c.latitude, c.longitude FROM c"
    existing = client.search_container_by_query(query, [])
    existing_coords = [
        (r["latitude"], r["longitude"])
        for r in existing
        if r.get("latitude") and r.get("longitude")
    ]

    st.caption("画像ファイルから座標登録")
    uploaded_files = st.file_uploader(
        "画像ファイルをアップロード（複数可）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )
    if uploaded_files and st.button("座標登録"):
        # 画像→座標抽出
        coords = []
        file_names = []
        for f in uploaded_files:
            f.seek(0)
            c = get_gps_coordinates(f.read())
            if c:
                coords.append(c)
                file_names.append(f.name)
        # 画像内15m以内の重複除去
        filtered = []
        for c in coords:
            if all(haversine(c[0], c[1], fc[0], fc[1]) > 1 for fc in filtered):
                filtered.append(c)
        # 既存座標と15m以内のものを除外
        new_points = []
        for c in filtered:
            if all(haversine(c[0], c[1], ec[0], ec[1]) > 1 for ec in existing_coords):
                new_points.append(c)
        # CosmosDBへ登録（id必須）
        # new_pointsとcoords/file_namesの順序を合わせるため、coords→filtered→new_pointsのindexを追跡
        to_insert = []
        for c in new_points:
            # filteredのindexを取得（coords, file_namesと同じ順序）
            try:
                idx = filtered.index(c)
                fname = file_names[idx]
            except Exception:
                fname = ""
            to_insert.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": fname,
                    "latitude": c[0],
                    "longitude": c[1],
                }
            )
        if to_insert:
            client.upsert_to_container(to_insert)
            st.success(f"{len(to_insert)}件の座標を登録しました")
        else:
            st.info("新規登録すべき座標はありませんでした")

    # 最新データ取得・地図表示
    traps = client.search_container_by_query(
        "SELECT c.latitude, c.longitude, c.name  FROM c", []
    )
    # Noneや不正なデータを除外
    traps = [
        r for r in traps if isinstance(r, dict) and "latitude" in r and "longitude" in r
    ]
    st.session_state["traps"] = traps
    st.subheader("地図上に座標を表示")
    show_map(traps)


if __name__ == "__main__" or True:
    main()
