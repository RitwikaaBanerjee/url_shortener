from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from database import engine, Base, get_db
import models
import schemas
from utils import create_random_code

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")

# Setup templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    urls = db.query(models.URLItem).all()
    return templates.TemplateResponse("index.html", {"request": request, "urls": urls})

@app.post("/shorten", response_class=HTMLResponse)
def shorten_url(
    request: Request, 
    url: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        # Basic validation handled by the URL input type in HTML and fastAPI Form
        valid_url = url
    except ValidationError:
        urls = db.query(models.URLItem).all()
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "urls": urls, "error": "Invalid URL format. Please provide a valid URL."}
        )

    # Check if URL already exists
    db_url = db.query(models.URLItem).filter(models.URLItem.original_url == str(valid_url)).first()
    if db_url:
        urls = db.query(models.URLItem).all()
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "urls": urls, "message": f"URL already shortened: {db_url.short_code}"}
        )
    
    # Generate unique short code
    short_code = create_random_code()
    while db.query(models.URLItem).filter(models.URLItem.short_code == short_code).first():
        short_code = create_random_code()
        
    db_item = models.URLItem(original_url=str(valid_url), short_code=short_code)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    # Redirect back to home
    return RedirectResponse(url="/", status_code=303)

@app.get("/{short_code}")
def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    db_url = db.query(models.URLItem).filter(models.URLItem.short_code == short_code).first()
    if db_url:
        db_url.clicks += 1
        db.commit()
        return RedirectResponse(url=db_url.original_url)
    
    raise HTTPException(status_code=404, detail="Short URL not found")
