import io
import requests
from ebooklib import epub
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = "https://yjztphrejsnurfqouubg.supabase.co"
SUPABASE_KEY = "sb_publishable_woyH5lIPpN0h9kqNSllXNw_-15-5h9q"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "epubs"

def sync_bucket_to_db():
    files = supabase.storage.from_(BUCKET_NAME).list()
    print("Files found in bucket:", files)
    existing_books = supabase.table("books").select("file_url").execute().data
    existing_urls = {b["file_url"] for b in existing_books}

    for f in files:
        
        file_name = f["name"]
        if not file_name.lower().endswith(".epub"):
            continue
        
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_name}"
        if public_url in existing_urls:
            continue
        
        print(f"New file found: {file_name}. Processing metadata...")
        res = requests.get(public_url)
        title = file_name.replace(".epub", "").replace("_", " ")
        author = "Unknown Author"

        try:
            book = epub.read_epub(io.BytesIO(res.content))
            
            t = book.get_metadata("DC", "title")
            if t:
                title = t[0][0]
                
            a = book.get_metadata("DC", "creator")
            if a:
                author = a[0][0]
        except Exception as err:
            print(f"Could not parse metadata for {file_name}, using filename instead. Error: {err}")
        
        supabase.table("books").insert({
            "title": title,
            "author": author,
            "file_url": public_url
        }).execute()
        
        print(f"Added '{title}' by {author} to database.")

if __name__ == "__main__":
    sync_bucket_to_db()