from PIL import Image
import piexif
import io
import requests
import streamlit.components.v1 as components


def get_location():
    html_code = """
    <script>
    function sendLocation() {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const latitude = position.coords.latitude.toFixed(4);
                const longitude = position.coords.longitude.toFixed(4);
                document.getElementById("location").innerText = 
                    `${latitude},${longitude}`;
            },
            function(error) {
                document.getElementById("location").innerText = "位置情報を取得できませんでした。";
            }
        );
    }
    sendLocation();
    </script>
    <div id="location">位置情報を取得中...</div>
    """
    components.html(html_code, height=30)


def get_gps_coordinates(file_data):
    img = Image.open(io.BytesIO(file_data))
    exif_data = img.info.get("exif")

    if not exif_data:
        print("No EXIF metadata found.")
        return None

    exif_dict = piexif.load(exif_data)
    gps_info = exif_dict.get("GPS", {})

    if not gps_info:
        print("No GPS data found.")
        return None

    def convert_to_degrees(value):
        """Convert GPS coordinates from EXIF format to degrees"""
        d, m, s = value
        return d[0] / d[1] + (m[0] / m[1]) / 60 + (s[0] / s[1]) / 3600

    try:
        lat = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLatitude])
        lon = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLongitude])

        # 北緯・南緯、東経・西経の補正
        if gps_info[piexif.GPSIFD.GPSLatitudeRef] != b"N":
            lat = -lat
        if gps_info[piexif.GPSIFD.GPSLongitudeRef] != b"E":
            lon = -lon

        return lat, lon
    except KeyError:
        print("Invalid GPS data format.")
        return None


def get_japanese_address(lat, lon):
    """緯度経度から日本の住所情報を取得する"""
    url = f"https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat={lat}&lon={lon}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            return data["results"]
        else:
            print("住所情報が見つかりませんでした。")
            return None
    else:
        print("リクエストに失敗しました。")
        return None


def get_address_from_muniCd(muniCd):
    """muni.jsを使って、muniCdから住所を検索する"""
    url = "https://maps.gsi.go.jp/js/muni.js"
    response = requests.get(url)

    if response.status_code == 200:
        content = response.text
        muni_dict = {}
        print("content==>")
        print(content)
        print(len(content.splitlines()))

        for i, line in enumerate(content.splitlines()):
            print(f"line {i} ==> {line}")
            if line.startswith("GSI.MUNI_ARRAY"):
                parts = line.split(" = ")
                key = parts[0].split('["')[1].split('"]')[0]
                value = parts[1].strip("';").split(",")
                if len(value) >= 4:
                    muni_dict[key] = value
        print("i==> ", i)

        if muniCd in muni_dict:
            return muni_dict[muniCd][1] + muni_dict[muniCd][3]
        else:
            print("指定されたmuniCdの住所が見つかりませんでした。")
            return None
    else:
        print("muni.jsのリクエストに失敗しました。")
        return None


# full_address, muniCd = get_full_address(34.610929, 137.113483)


def get_full_address(lat, lon):
    address_info = get_japanese_address(lat, lon)
    if address_info:
        muniCd = address_info[0].get("muniCd")
        if muniCd:
            full_address = get_address_from_muniCd(muniCd)
            return full_address, muniCd
        else:
            print("muniCdが見つかりませんでした。")
            return None, None
    else:
        print("住所情報が見つかりませんでした。")
        return None, None
