import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from st_init import with_init

st.set_page_config(page_title="わな稼働状況", layout="wide", page_icon="🐗")


@with_init
def main():
    st.subheader("わな稼働状況")

    if st.session_state.user is None:
        st.warning("最初の画面でログインをしてください。")
        return

    traps = st.session_state.traps
    df = pd.DataFrame(traps)

    # 日付処理
    today = datetime.now().date()
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce").fillna(
        pd.to_datetime(today)
    )

    # 表示用ラベル
    df["label"] = df["trap_type"] + " - " + df["trap_name"]

    # 色マッピング
    status_colors = {"稼働中": "green", "撤去済み": "gray"}

    # Altair ガントチャート
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("start_date:T", title="開始日", axis=alt.Axis(format="%m/%d")),
            x2="end_date:T",
            y=alt.Y("label:N", sort=None, title="わな種別 - 名前"),
            color=alt.Color(
                "status:N",
                scale=alt.Scale(
                    domain=list(status_colors.keys()),
                    range=list(status_colors.values()),
                ),
            ),
            tooltip=[
                "trap_type",
                "trap_name",
                "status",
                alt.Tooltip("start_date:T", title="開始日", format="%Y-%m-%d"),
                alt.Tooltip("end_date:T", title="終了日", format="%Y-%m-%d"),
            ],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    main()
