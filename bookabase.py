import io
import os
import requests
import streamlit as st
from supabase import create_client, Client
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from sync_books import sync_bucket_to_db

primaryColor = "#FF8700"

st.set_page_config(
    page_title="BOOKABASE",
    page_icon="📚",
    layout="wide",
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://yjztphrejsnurfqouubg.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_woyH5lIPpN0h9kqNSllXNw_-15-5h9q")

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

if "current_book" not in st.session_state:
    st.session_state.current_book = None
if "chapters" not in st.session_state:
    st.session_state.chapters = []
if "current_chapter_idx" not in st.session_state:
    st.session_state.current_chapter_idx = 0

def load_books():
    try:
        sync_bucket_to_db()
    except Exception as e:
        st.warning(f"Error syncing bucket: {e}")
    
    response = supabase.table("books").select("*").execute()
    return response.data or []

@st.cache_data(show_spinner=False)
def parse_epub_from_url(file_url: str) -> list[str]:
    res = requests.get(file_url, timeout=15)
    epub_book = epub.read_epub(io.BytesIO(res.content))

    parsed_chapters = []

    for item in epub_book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            content = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")
            
            for tag in soup(["script", "style"]):
                tag.decompose()

            body = soup.body
            if body and len(body.get_text(strip=True)) > 20:
                parsed_chapters.append(str(body))

    if not parsed_chapters:
        for item in epub_book.get_items():
            content = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(strip=True)
            if len(text) > 50:
                parsed_chapters.append(f"<div>{str(soup)}</div>")

    return parsed_chapters if parsed_chapters else ["<p>No readable chapters found in this book.</p>"]

def open_book(book: dict):
    st.session_state.current_book = book
    st.session_state.current_chapter_idx = 0
    with st.spinner("Downloading and parsing EPUB..."):
        try:
            st.session_state.chapters = parse_epub_from_url(book["file_url"])
        except Exception as e:
            st.error(f"Failed to load book: {e}")
            st.session_state.chapters = ["<p>Error loading book content.</p>"]

def close_reader():
    st.session_state.current_book = None
    st.session_state.chapters = []
    st.session_state.current_chapter_idx = 0

def render_library_view():
    st.markdown(
        """
        <h1 style='text-align: center; color: orange; font-family: "Roboto Mono", monospace; margin-top: 2rem;'>
            B O O K A B A S E
        </h1>
        """,
        unsafe_allow_html=True,
    )

    search_query = st.text_input(
        "Search library",
        placeholder="Search by title or author...",
        label_visibility="collapsed",
    )

    books = load_books()

    if search_query:
        q = search_query.lower()
        books = [
            b for b in books
            if q in b.get("title", "").lower() or q in b.get("author", "").lower()
        ]

    st.write("")

    if not books:
        st.info("No books found.")
        return

    col1, col2, col3 = st.columns([4, 4, 2])
    with col1:
        st.markdown("**Title**")
    with col2:
        st.markdown("**Author**")
    with col3:
        st.markdown("**Action**")

    st.divider()

    st.html("<style>div.stButton > button[data-testid='stBaseButton-primary'] { width: 100px !important; }</style>")

    for book in books:
        c1, c2, c3 = st.columns([4, 4, 2])
        with c1:
            st.write(book.get("title", "Untitled"))
        with c2:
            st.write(book.get("author", "Unknown"))
        with c3:
            if st.button("Read", key=f"read_{book.get('id', book.get('title'))}", type="primary",):
                open_book(book)
                st.rerun()

def render_reader_view():
    book = st.session_state.current_book
    chapters = st.session_state.chapters
    idx = st.session_state.current_chapter_idx

    top_col1, top_col2, top_col3 = st.columns([2, 5, 3], vertical_alignment="center")
    
    with top_col1:
        if st.button("← Back to BookaBase"):
            close_reader()
            st.rerun()

    with top_col2:
        st.markdown(
            f"<h3 style='color: orange; font-family: \"Roboto Mono\", monospace; margin: 0;'>"
            f"{book.get('title', 'Untitled')}</h3>",
            unsafe_allow_html=True,
        )

    with top_col3:
        nav_c1, nav_c2, nav_c3 = st.columns([1, 1, 1], vertical_alignment="center")
        with nav_c1:
            if st.button("< Prev", disabled=(idx <= 0)):
                st.session_state.current_chapter_idx -= 1
                st.rerun()
        with nav_c2:
            st.write(f"Ch. {idx + 1}/{len(chapters)}")
        with nav_c3:
            if st.button("Next >", disabled=(idx >= len(chapters) - 1)):
                st.session_state.current_chapter_idx += 1
                st.rerun()

    st.divider()

    content_container = st.container()
    with content_container:
        if chapters and 0 <= idx < len(chapters):
            st.components.v1.html(
                f"""
                <div style="
                    font-family: 'Georgia', serif; 
                    line-height: 1.8; 
                    color: #e2e8f0; 
                    background-color: transparent; 
                    padding: 20px;
                    font-size: 18px;
                ">
                    <style>
                        p {{ color: #e2e8f0 !important; }}
                        h1, h2, h3, h4 {{ color: #ffa500 !important; }}
                        a {{ color: #3182ce !important; }}
                    </style>
                    {chapters[idx]}
                </div>
                """,
                height=750,
                scrolling=True,
            )

if st.session_state.current_book is None:
    render_library_view()
else:
    render_reader_view()