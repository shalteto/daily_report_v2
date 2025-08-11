import streamlit as st
from page_parts.upload_result_report import upsert_catch_result


from st_init import with_init


@with_init
def main():
    upsert_catch_result()


if __name__ == "__main__":
    main()
