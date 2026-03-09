from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import HttpUrl, ValidationError

from database import get_db, urls_collection
import schemas
from utils import create_random_code
from bson import ObjectId

app = FastAPI(title="URL Shortener")

# Setup templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    # Retrieve all documents from MongoDB
    urls_cursor = urls_collection.find({})
    
    # Convert MongoDB documents to dictionaries suitable for Jinja
    urls = []
    for doc in urls_cursor:
        urls.append({
            "id": str(doc["_id"]),
            "original_url": doc["original_url"],
            "short_code": doc["short_code"],
            "clicks": doc.get("clicks", 0)
        })
        
    return templates.TemplateResponse("index.html", {"request": request, "urls": urls})

@app.post("/shorten", response_class=HTMLResponse)
def shorten_url(
    request: Request, 
    url: str = Form(...)
):
    # Validate URL
    try:
        valid_url = schemas.URLBase(original_url=url).original_url
    except ValidationError:
        urls_cursor = urls_collection.find({})
        urls = [{"id": str(d["_id"]), "original_url": d["original_url"], "short_code": d["short_code"], "clicks": d.get("clicks", 0)} for d in urls_cursor]
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "urls": urls, "error": "Invalid URL format. Please provide a valid URL."}
        )

    # Check if URL already exists
    db_url = urls_collection.find_one({"original_url": str(valid_url)})
    if db_url:
        urls_cursor = urls_collection.find({})
        urls = [{"id": str(d["_id"]), "original_url": d["original_url"], "short_code": d["short_code"], "clicks": d.get("clicks", 0)} for d in urls_cursor]
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "urls": urls, "message": f"URL already shortened: {db_url['short_code']}"}
        )
    
    # Generate unique short code
    short_code = create_random_code()
    while urls_collection.find_one({"short_code": short_code}):
        short_code = create_random_code()
        
    new_url_item = {
        "original_url": str(valid_url),
        "short_code": short_code,
        "clicks": 0
    }
    
    urls_collection.insert_one(new_url_item)
    
    # Redirect back to home
    return RedirectResponse(url="/", status_code=303)

@app.get("/{short_code}")
def redirect_to_url(short_code: str):
    db_url = urls_collection.find_one({"short_code": short_code})
    
    if db_url:
        # Increment click count using $inc
        urls_collection.update_one(
            {"_id": db_url["_id"]},
            {"$inc": {"clicks": 1}}
        )
        return RedirectResponse(url=db_url["original_url"])
    
    raise HTTPException(status_code=404, detail="Short URL not found")
