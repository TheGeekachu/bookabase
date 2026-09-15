import reflex as rx

class Book(rx.Model, table=True):
    title: str
    author: str
    filepath: str
    cover_path: str
    current_chapter: int = 0
    total_chapters: int = 0
    progress_percent: float = 0.0