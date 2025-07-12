import streamlit as st
from datetime import datetime
import uuid
from azure_.cosmosdb import CosmosDBClient


def input_order():
    client = st.session_state["cosmos_client"]
    st.subheader("受注情報入力")
    with st.form(key="input_order_form"):
        customer_name = st.text_input("発注元")
        order_name = st.text_input("事業名")
        area = st.text_input("実施地区")
        start_date = st.date_input("開始日")
        end_date = st.date_input("終了日")
        this_year = datetime.now().year
        order_year = st.number_input(
            "実施年度", min_value=1, max_value=this_year + 3, value=this_year
        )
        submit_button = st.form_submit_button(label="送信")

    if submit_button:
        if customer_name and order_name and area and start_date and end_date:
            with st.spinner("送信中...", show_time=True):
                data = {
                    "id": str(uuid.uuid4()),
                    "category": "order",
                    "customer_name": customer_name,
                    "order_name": order_name,
                    "year": order_year,
                    "area": area,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                }
                client.upsert_to_container(data)
                st.session_state["orders"].append(data)
            st.success("送信完了")
        else:
            if not customer_name:
                st.error("発注元を選択してください。")
            if not order_name:
                st.error("事業名を入力してください。")
            if not area:
                st.error("実施地区を入力してください。")
            if not start_date:
                st.error("開始日を入力してください。")
            if not end_date:
                st.error("終了日を入力してください。")


def edit_order():
    st.subheader("受注情報編集")
    client = st.session_state["cosmos_client"]
    orders = st.session_state["orders"]
    if not orders:
        st.warning("受注情報がありません。")
        return
    order_options = (
        [f"{u['area']} / {u['year']}（{u['order_name']}）" for u in orders]
        if orders
        else []
    )
    selected_idx = (
        st.selectbox(
            "編集する受注情報を選択",
            range(len(order_options)),
            format_func=lambda i: order_options[i] if order_options else "",
            key="user_select",
            index=0 if orders else None,
        )
        if orders
        else None
    )

    if selected_idx is not None:
        selected_order = orders[selected_idx]
        if selected_order:
            with st.form(key="edit_order_form"):
                customer_name = st.text_input(
                    "発注元", value=selected_order["customer_name"]
                )
                order_name = st.text_input("事業名", value=selected_order["order_name"])
                area = st.text_input("実施地区", value=selected_order["area"])
                start_date = st.date_input(
                    "開始日",
                    value=datetime.strptime(selected_order["start_date"], "%Y-%m-%d"),
                )
                end_date = st.date_input(
                    "終了日",
                    value=datetime.strptime(selected_order["end_date"], "%Y-%m-%d"),
                )
                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button(label="更新")
                with col2:
                    delete_button = st.form_submit_button(label="削除")

            if submit_button:
                if customer_name and order_name and area and start_date and end_date:
                    with st.spinner("更新中...", show_time=True):
                        updated_data = {
                            "id": selected_order["id"],
                            "category": "order",
                            "customer_name": customer_name,
                            "order_name": order_name,
                            "year": selected_order["year"],
                            "area": area,
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d"),
                        }
                        client.upsert_to_container(updated_data)
                        st.session_state["users"][selected_idx] = updated_data
                    st.success("更新完了")
                else:
                    if not customer_name:
                        st.error("発注元を入力してください。")
                    if not order_name:
                        st.error("事業名を入力してください。")
                    if not area:
                        st.error("実施地区を入力してください。")
                    if not start_date:
                        st.error("開始日を入力してください。")
                    if not end_date:
                        st.error("終了日を入力してください。")
            if delete_button:
                with st.spinner("削除中...", show_time=True):
                    client.delete_item_from_container(selected_order["id"], "order")
                    st.session_state["orders"].pop(selected_idx)
                st.success("受注情報を削除しました。")
                st.rerun()
