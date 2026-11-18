import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from .db import *
from .config import settings
hasher = PasswordHasher()
DUMMY = hasher.hash('constant-time-missing-user-placeholder')

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
def issue(db,user,response,absolute=None):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    expiry = min(now()+1800, absolute or now()+86400)
    db.add(Session(user_id=user.id,token_hash=token_hash(token),csrf=csrf,expires=expiry,absolute_expires=absolute or now()+86400))
    response.set_cookie('prooflane_session',token,httponly=True,secure=settings().cookie_secure,samesite='strict',max_age=int(expiry-now()),path='/')
    return csrf

def current(request:Request,db=Depends(database)):
    token = request.cookies.get('prooflane_session','')
    sess = db.scalar(select(Session).where(Session.token_hash==token_hash(token)))
    if not sess or sess.expires<=now() or sess.absolute_expires<=now(): raise HTTPException(401,'Session expired')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if request.headers.get('origin') != settings().public_origin or not secrets.compare_digest(request.headers.get('x-csrf-token',''),sess.csrf):
            raise HTTPException(403,'CSRF validation failed')
    user=db.get(User,sess.user_id)
    request.state.auth_session=sess
    return user

def researcher(user=Depends(current)):
    if user.role!='researcher': raise HTTPException(403,'Researcher role required')
    return user
