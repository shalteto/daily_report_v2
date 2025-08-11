import streamlit as st
from page_parts.result_graph import show_graph, show_map


from st_init import with_init


@with_init
def main():
    show_graph()
    st.markdown("---")
    show_map()



if __name__ == "__main__":
    main()
