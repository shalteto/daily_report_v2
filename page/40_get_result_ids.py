import streamlit as st
from page_parts.get_result_ids import result_id_display


from st_init import with_init


@with_init
def main():
    result_id_display()


if __name__ == "__main__":
    main()
