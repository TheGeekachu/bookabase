import reflex as rx
import io
import requests
from supabase import create_client, Client
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from .sync_books import sync_bucket_to_db

SUPABASE_URL = "https://yjztphrejsnurfqouubg.supabase.co"
SUPABASE_KEY = "sb_publishable_woyH5lIPpN0h9kqNSllXNw_-15-5h9q"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class State(rx.State):
    books: list[dict] = []
    search_query: str = ""
    current_book: dict | None = None
    chapters: list[str] = []
    current_chapter_idx: int = 0

    def load_library(self):
        try:
            sync_bucket_to_db()
        except Exception as e:
            print(f"Error syncing bucket: {e}")
        response = supabase.table("books").select("*").execute()
        self.books = response.data
        print("Loaded books into Reflex State:", self.books)

    def set_search_query(self, query: str):
        self.search_query = query

    @rx.var
    def filtered_books(self) -> list[dict]:
        if not self.search_query:
            return self.books
        q = self.search_query.lower()
        return [
            b for b in self.books
            if q in b.get("title", "").lower() or q in b.get("author", "").lower()
        ]
    
    def select_book(self, book: dict):
        self.current_book = book
        self.current_chapter_idx = 0

        res = requests.get(book["file_url"])
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

        self.chapters = parsed_chapters if parsed_chapters else ["<p>No readable chapters found in this book.</p>"]

    def close_reader(self):
        self.current_book = None
        self.chapters = []

    def next_chapter(self):
        if self.current_chapter_idx < len(self.chapters) - 1:
            self.current_chapter_idx += 1
    
    def prev_chapter(self):
        if self.current_chapter_idx > 0:
            self.current_chapter_idx -= 1

def book_row(book: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(book.get("title", "Untitled")),
        rx.table.cell(book.get("author", "Unknown")),
        rx.table.cell(
            rx.button("Read", on_click=lambda: State.select_book(book), size="1")
        ),
    )

def library_view() -> rx.Component:
    return rx.vstack(
        rx.heading("BookaBase", size="6"),
        rx.input(
            placeholder="Search by title or author...",
            on_change=State.set_search_query,
            width="100%",
            max_width="400px",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Title"),
                    rx.table.column_header_cell("Author"),
                    rx.table.column_header_cell("Action"),
                )
            ),
            rx.table.body(
                rx.foreach(State.filtered_books, book_row)
            ),
            width="100%",
        ),
        spacing="4",
        padding="6",
        max_width="800px",
    )

def reader_view() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.button("← Back to BookaBase", on_click=State.close_reader),
            rx.heading(State.current_book["title"], size="5"),
            rx.hstack(
                rx.button("< Previous", on_click=State.prev_chapter),
                rx.text(f"Chapter {State.current_chapter_idx + 1}"),
                rx.button("Next >", on_click=State.next_chapter),
            ),
            justify="between",
            width="100%",
            padding="4",
            border_bottom="1px solid #e5e7eb",
        ),
        rx.box(
            rx.html(State.chapters[State.current_chapter_idx]),
            width="100%",
            max_width="750px",
            padding="6",
        ),
        align_items="center",
        width="100%",
    )

def index() -> rx.Component:
    return rx.cond(
        State.current_book,
        reader_view(),
        library_view(),
    )

app = rx.App()
app.add_page(index, on_load=State.load_library)