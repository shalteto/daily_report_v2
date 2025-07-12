import streamlit as st
import pandas as pd
import pydeck as pdk
from PIL import Image
import piexif
import io
import math
import uuid

# from azure_.cosmosdb import CosmosDBClient # 今回の実行ではコメントアウト


# ダミーのCosmosDBClientクラス
class CosmosDBClient:
    def __init__(self, container_name):
        self.container_name = container_name
        self.items = []  # データを保持するリスト

    def search_container_by_query(self, query, params):
        # 簡単なクエリシミュレーション
        if "SELECT c.latitude, c.longitude FROM c" in query:
            return [
                {"latitude": item["latitude"], "longitude": item["longitude"]}
                for item in self.items
                if "latitude" in item and "longitude" in item
            ]
        elif "SELECT c.latitude, c.longitude, c.name FROM c" in query:
            return self.items
        return []

    def upsert_to_container(self, new_items):
        for item in new_items:
            # 既存のIDがあれば更新、なければ追加
            found = False
            for i, existing_item in enumerate(self.items):
                if existing_item.get("id") == item.get("id"):
                    self.items[i] = item
                    found = True
                    break
            if not found:
                self.items.append(item)


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


# --- 3次メッシュ関連関数 ---
def latlon_to_meshcode(lat, lon, level=3):
    """
    緯度経度から地域メッシュコードを計算します。
    ここでは3次メッシュのみを対象とします。
    """
    if level != 3:
        st.error("現在、3次メッシュのみをサポートしています。")
        return None

    # 1次メッシュ
    p1 = int(lat * 1.5)
    u1 = int((lon - 100) / 1)

    # 2次メッシュ
    p2 = int((lat * 1.5 - p1) * 8)
    u2 = int(((lon - 100) - u1) * 8)

    # 3次メッシュ
    p3 = int(((lat * 1.5 - p1) * 8 - p2) * 10)
    u3 = int((((lon - 100) - u1) * 8 - u2) * 10)

    mesh_code = f"{p1}{u1}{p2}{u2}{p3}{u3}"
    return mesh_code


def meshcode_to_latlon_bounds(mesh_code, level=3):
    """
    地域メッシュコードから緯度経度の境界を計算します。
    """
    if level != 3 or len(mesh_code) != 8:
        st.error(
            "現在、3次メッシュのみをサポートしており、メッシュコードは8桁である必要があります。"
        )
        return None

    p1 = int(mesh_code[0:2])
    u1 = int(mesh_code[2:4])
    p2 = int(mesh_code[4])
    u2 = int(mesh_code[5])
    p3 = int(mesh_code[6])
    u3 = int(mesh_code[7])

    # 南西端の緯度経度
    lat_sw = (p1 + p2 / 8 + p3 / 80) / 1.5
    lon_sw = (u1 + u2 / 8 + u3 / 80) + 100

    # 北東端の緯度経度
    lat_ne = (p1 + p2 / 8 + p3 / 80 + 1 / 80) / 1.5
    lon_ne = (u1 + u2 / 8 + u3 / 80 + 1 / 80) + 100

    return {
        "south_west": (lat_sw, lon_sw),
        "north_east": (lat_ne, lon_ne),
        "north_west": (lat_ne, lon_sw),
        "south_east": (lat_sw, lon_ne),
    }


def generate_mesh_polygons(bbox_ne, bbox_sw):
    """
    指定された範囲（北東、南西の緯度経度）をカバーする3次メッシュのポリゴンを生成します。
    bbox_ne: (lat, lon) 北東の端
    bbox_sw: (lat, lon) 南西の端
    """
    mesh_polygons = []

    lat_ne, lon_ne = bbox_ne
    lat_sw, lon_sw = bbox_sw

    # 範囲の南西端と北東端のメッシュコードを取得
    mesh_code_sw = latlon_to_meshcode(lat_sw, lon_sw)
    mesh_code_ne = latlon_to_meshcode(lat_ne, lon_ne)

    if not mesh_code_sw or not mesh_code_ne:
        return []

    # メッシュコードから、P, Uの部分を取り出し、開始と終了のインデックスを決定
    p1_sw, u1_sw, p2_sw, u2_sw, p3_sw, u3_sw = (
        int(mesh_code_sw[0:2]),
        int(mesh_code_sw[2:4]),
        int(mesh_code_sw[4]),
        int(mesh_code_sw[5]),
        int(mesh_code_sw[6]),
        int(mesh_code_sw[7]),
    )
    p1_ne, u1_ne, p2_ne, u2_ne, p3_ne, u3_ne = (
        int(mesh_code_ne[0:2]),
        int(mesh_code_ne[2:4]),
        int(mesh_code_ne[4]),
        int(mesh_code_ne[5]),
        int(mesh_code_ne[6]),
        int(mesh_code_ne[7]),
    )

    # 1次メッシュの範囲を確定
    p1_start = p1_sw
    p1_end = p1_ne if p1_ne >= p1_sw else p1_sw  # 北東の方が緯度が高い
    u1_start = u1_sw
    u1_end = u1_ne if u1_ne >= u1_sw else u1_sw  # 東の方が経度が高い

    # 全ての3次メッシュを網羅するようにループ
    # 実際には、P1U1P2U2P3U3の各桁を基準にループします
    # 緯度方向 (p)
    # 経度方向 (u)

    # 緯度方向のメッシュインデックスの開始と終了を計算
    # 1次メッシュのP、2次メッシュのP、3次メッシュのPの最小値と最大値を計算
    min_p_index = int(lat_sw * 1.5 * 80)  # 3次メッシュの緯度インデックスの最小値
    max_p_index = math.ceil(lat_ne * 1.5 * 80)  # 3次メッシュの緯度インデックスの最大値

    # 経度方向のメッシュインデックスの開始と終了を計算
    # 1次メッシュのU、2次メッシュのU、3次メッシュのUの最小値と最大値を計算
    min_u_index = int((lon_sw - 100) * 80)  # 3次メッシュの経度インデックスの最小値
    max_u_index = math.ceil(
        (lon_ne - 100) * 80
    )  # 3次メッシュの経度インデックスの最大値

    for p_idx in range(min_p_index, max_p_index + 1):
        for u_idx in range(min_u_index, max_u_index + 1):

            p1_val = p_idx // 80
            p2_val = (p_idx % 80) // 10
            p3_val = (p_idx % 80) % 10

            u1_val = u_idx // 80
            u2_val = (u_idx % 80) // 10
            u3_val = (u_idx % 80) % 10

            current_mesh_code = (
                f"{p1_val:02d}{u1_val:02d}{p2_val}{u2_val}{p3_val}{u3_val}"
            )
            bounds = meshcode_to_latlon_bounds(current_mesh_code)

            if bounds:
                polygon = [
                    [bounds["south_west"][1], bounds["south_west"][0]],  # SW (lon, lat)
                    [bounds["south_east"][1], bounds["south_east"][0]],  # SE (lon, lat)
                    [bounds["north_east"][1], bounds["north_east"][0]],  # NE (lon, lat)
                    [bounds["north_west"][1], bounds["north_west"][0]],  # NW (lon, lat)
                    [bounds["south_west"][1], bounds["south_west"][0]],  # SWに戻る
                ]
                mesh_polygons.append({"path": polygon, "code": current_mesh_code})

    return mesh_polygons


# --- 地図表示 ---
def show_map(trap_points, mesh_polygons=None):
    if not trap_points and not mesh_polygons:
        st.warning("表示するデータがありません。")
        return

    layers = []

    # わな設置点のレイヤー
    if trap_points:
        filtered = [r for r in trap_points if "latitude" in r and "longitude" in r]
        if filtered:
            df = pd.DataFrame(filtered)
            df["color"] = [[0, 255, 0, 160]] * len(df)
            layer_trap_points = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position="[longitude, latitude]",
                get_radius=50,
                get_color="color",
                pickable=True,
                auto_highlight=True,
                id="trap_points_layer",
            )
            layers.append(layer_trap_points)
            center_lat = df["latitude"].mean()
            center_lon = df["longitude"].mean()
        else:
            center_lat = 34.6321655  # デフォルトの中心
            center_lon = 137.150609  # デフォルトの中心
    else:
        # メッシュポリゴンのみの場合、メッシュ範囲の中心を計算
        if mesh_polygons:
            all_lats = []
            all_lons = []
            for mp in mesh_polygons:
                for coord in mp["path"]:
                    all_lons.append(coord[0])
                    all_lats.append(coord[1])
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
        else:
            center_lat = 34.6321655  # デフォルトの中心
            center_lon = 137.150609  # デフォルトの中心

    # 3次メッシュポリゴンのレイヤー
    if mesh_polygons:
        df_mesh = pd.DataFrame(mesh_polygons)
        layer_mesh_polygons = pdk.Layer(
            "PolygonLayer",
            data=df_mesh,
            get_polygon="path",
            filled=True,
            stroked=True,
            get_fill_color=[0, 0, 255, 20],  # 塗りつぶしの色 (青、透明度低め)
            get_line_color=[0, 0, 255, 150],  # 線の色 (青)
            get_line_width=50,
            pickable=True,
            auto_highlight=True,
            id="mesh_polygons_layer",
        )
        layers.append(layer_mesh_polygons)

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

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=14)
    chart = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip={
            "html": "<b>メッシュコード:</b> {code}<br/><b>名前:</b> {name}"
        },  # メッシュコードと名前を表示
    )
    # 複数選択・選択イベント対応
    event = st.pydeck_chart(
        chart,
        selection_mode="multi-object",
        on_select="rerun",
        height=600,
    )
    # 選択されたメッシュコードを抽出して表示
    selected_codes = []
    if (
        hasattr(event, "selection")
        and "objects" in event.selection
        and event.selection["objects"]
    ):
        selected_meshes = event.selection["objects"].get("mesh_polygons_layer", [])
        selected_codes = [obj.get("code") for obj in selected_meshes if "code" in obj]
        st.session_state.selected_mesh_codes = selected_codes
    else:
        st.session_state.selected_mesh_codes = []
    if st.session_state.selected_mesh_codes:
        st.info(
            "選択中のメッシュコード: " + ", ".join(st.session_state.selected_mesh_codes)
        )


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

    # 最新データ取得
    traps = client.search_container_by_query(
        "SELECT c.latitude, c.longitude, c.name FROM c", []
    )
    # Noneや不正なデータを除外
    traps = [
        r for r in traps if isinstance(r, dict) and "latitude" in r and "longitude" in r
    ]
    st.session_state["traps"] = traps

    st.subheader("地図上に座標を表示")

    # メッシュ生成範囲の定義
    # 北東の端：34.680930, 137.218362
    # 南西の端：34.583401, 137.082856
    bbox_ne = (34.680930, 137.218362)
    bbox_sw = (34.583401, 137.082856)

    # 3次メッシュポリゴンの生成
    mesh_polygons = generate_mesh_polygons(bbox_ne, bbox_sw)

    show_map(traps, mesh_polygons)


if __name__ == "__main__":
    main()
