import streamlit as st

def main():
    # タイトルの表示
    # st.title('トップページです。')
    # st.markdown("---")
    # st.markdown("ここにいろいろと説明を書いていきます。")

    with open('top.md', 'r') as f:
        readme_content = f.read()

    st.markdown(readme_content)

if __name__ == '__main__':
    main()
