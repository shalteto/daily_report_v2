# pip install
from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO


def create_info_band(data: dict, width: int, font_path: str = None) -> Image.Image:
    """
    データ辞書を受け取り、フォントサイズと行数に応じて高さを自動調整した帯画像を生成
    """
    # フォント設定
    if font_path is None:
        font_path = os.path.join(os.path.dirname(__file__), "NotoSansJP-Regular.otf")
        print(f"フォントパス: {font_path}")
    try:
        font_size = 80
        font = ImageFont.truetype(font_path, font_size)
        print(f"フォントを読み込みました: {font_path}")
    except Exception:
        font = ImageFont.load_default()
        font_size = 80  # デフォルトフォントの推定サイズ
        print(f"フォントの読み込みに失敗しました。デフォルトフォントを使用します。")

    # 行ごとの高さ（フォントサイズ × 1.2 でゆとりを持たせる）
    line_spacing = int(font_size * 1.2)
    num_lines = len(data)
    padding_top_bottom = 20

    # 帯の高さを自動で計算
    height = padding_top_bottom * 2 + line_spacing * num_lines

    # 帯画像作成
    band = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(band)

    # テキスト描画
    x, y = 20, padding_top_bottom
    for k, v in data.items():
        text = f"{k}: {v}"
        draw.text((x, y), text, fill=(0, 0, 0), font=font)
        y += line_spacing

    return band


def combine_images_with_band(
    base_img_path: str,
    data: dict,
    permit_img_path: str = None,  # ファイルパスまたはbytes
    font_path: str = None,
    output_path: str = "output.png",
):
    """
    base_img_path: 被写体画像パス
    data: 帯に描画するデータ辞書
    permit_img_path: 許可証画像パスまたは画像バイナリ(bytes)
    font_path: 日本語フォントパス
    output_path: 保存先
    """
    base_img = Image.open(base_img_path)
    width, height = base_img.width, base_img.height  # 4000x2000
    aspect_ratio = height / width  # 0.5
    permit_img = None
    permit_w, permit_h = 0, 0
    if permit_img_path:
        if isinstance(permit_img_path, bytes):
            permit_img = Image.open(BytesIO(permit_img_path))
        else:
            permit_img = Image.open(permit_img_path)
        permit_width, permit_height = permit_img.width, permit_img.height  # 800x600
        # 許可証画像のリサイズ
        if aspect_ratio > 1.2:
            # 縦長:
            max_permit_w = int(width * 0.65)
            scale = max_permit_w / permit_width
            permit_w = int(permit_width * scale)
            permit_h = int(permit_height * scale)
            permit_img = permit_img.resize((permit_w, permit_h))
        else:
            # 横長:
            max_permit_h = int(height * 0.4)
            scale = max_permit_h / permit_height
            permit_w = int(permit_width * scale)
            permit_h = int(permit_height * scale)
            permit_img = permit_img.resize((permit_w, permit_h))

    if aspect_ratio > 1.2:
        # 縦長: ベース画像の右上に許可証画像、その下に帯画像
        band_width = permit_w if permit_img else int(width * 0.45)
        # 帯画像の幅は許可証画像に合わせる
        band = create_info_band(data, band_width, font_path=font_path)
        total_band_height = (permit_h if permit_img else 0) + band.height
        new_width = width + band_width
        new_height = max(height, total_band_height)
        new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
        new_img.paste(base_img, (0, 0))
        # 許可証画像を右上に
        if permit_img:
            new_img.paste(permit_img, (width, 0))
        # 帯画像を許可証画像の下に
        new_img.paste(band, (width, permit_h if permit_img else 0))
    else:
        # 横長: ベース画像の下側左側に許可証画像、その右側の空白に帯画像
        band_height = permit_h if permit_img else int(height * 0.18)
        # 帯画像の幅はベース画像の幅-許可証画像の幅
        band_width = max(width - permit_w, 1) if permit_img else width
        band = create_info_band(data, band_width, font_path=font_path)
        new_width = width
        new_height = height + max(band_height, band.height)
        new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
        new_img.paste(base_img, (0, 0))
        # 許可証画像を下側左側に
        if permit_img:
            new_img.paste(permit_img, (0, height))
        # 帯画像を許可証画像の右側（空白部分）に
        band_x = permit_w if permit_img else 0
        band_y = height
        new_img.paste(band, (band_x, band_y))
    new_img.save(output_path)
    print(f"保存しました: {output_path}")
    return output_path


# 使用例
if __name__ == "__main__":
    data = {
        "捕獲日": "2025-05-06",
        "委託業務名": "渥美地区野生イノシシ根絶事業",
        "実施地域": "渥美地区",
        "捕獲者": "鈴木翔一郎",
    }
    data2 = {
        "実施日": "2025-05-06",
        "委託業務名": "渥美地区野生イノシシ根絶事業",
        "実施地域": "渥美地区",
        "従事人数": "12",
    }
    combine_images_with_band(
        "image01.JPG",
        data,
        permit_img_path="許可証.png",
        font_path="NotoSansJP-Regular.ttf",
        output_path="result.jpg",
    )
