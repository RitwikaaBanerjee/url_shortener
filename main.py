from fastapi import FastAPI, Depends, HTTPException, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import engine, Base, get_db
import models
from utils import create_random_code
from auth import verify_password, get_password_hash, create_access_token, get_current_user_from_cookie

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Link Management Platform")
templates = Jinja2Templates(directory="templates")

def get_current_user(request: Request, db: Session = Depends(get_db)):
    username = get_current_user_from_cookie(request)
    if not username:
        return None
    user = db.query(models.User).filter(models.User.username == username).first()
    return user

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    
    urls = db.query(models.URLItem).filter(models.URLItem.user_id == user.id).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "urls": urls, "user": user})

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Username already exists."})
    
    hashed_pass = get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_pass)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return templates.TemplateResponse("login.html", {"request": request, "message": "Registration successful! Please login."})

@app.post("/login", response_class=HTMLResponse)
def login(response: Response, request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."})
    
    access_token_expires = timedelta(minutes=60*24*7)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    redirect_resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect_resp.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return redirect_resp

@app.get("/logout")
def logout(response: Response):
    redirect_resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect_resp.delete_cookie("access_token")
    return redirect_resp

@app.post("/shorten")
def shorten_url(
    request: Request, 
    url: str = Form(...), 
    max_clicks: int = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=303)

    short_code = create_random_code()
    while db.query(models.URLItem).filter(models.URLItem.short_code == short_code).first():
        short_code = create_random_code()
        
    db_item = models.URLItem(
        original_url=url, 
        short_code=short_code, 
        user_id=user.id,
        max_clicks=max_clicks if max_clicks and max_clicks > 0 else None
    )
    db.add(db_item)
    db.commit()
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/edit/{short_code}")
def edit_url(
    short_code: str,
    request: Request,
    original_url: str = Form(...),
    max_clicks: int = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=303)
        
    db_url = db.query(models.URLItem).filter(models.URLItem.short_code == short_code, models.URLItem.user_id == user.id).first()
    if db_url:
        db_url.original_url = original_url
        db_url.max_clicks = max_clicks if max_clicks and max_clicks > 0 else None
        db.commit()
        
    return RedirectResponse(url="/", status_code=303)

@app.post("/toggle/{short_code}")
def toggle_status(short_code: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=303)
        
    db_url = db.query(models.URLItem).filter(models.URLItem.short_code == short_code, models.URLItem.user_id == user.id).first()
    if db_url:
        db_url.is_enabled = not db_url.is_enabled
        db.commit()
        
    return RedirectResponse(url="/", status_code=303)

@app.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):
    db_url = db.query(models.URLItem).filter(models.URLItem.short_code == short_code).first()
    if not db_url:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Short URL not found."})
        
    if not db_url.is_enabled:
        return templates.TemplateResponse("error.html", {"request": request, "message": "This link is currently inactive."})
        
    if db_url.max_clicks and db_url.clicks >= db_url.max_clicks:
        return templates.TemplateResponse("error.html", {"request": request, "message": "This link has expired (click limit reached)."})
        
    db_url.clicks += 1
    db_url.last_accessed_at = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url=db_url.original_url)
