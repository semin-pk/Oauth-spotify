from fastapi import FastAPI, Depends, Request
import urllib.parse
import pkce
import requests
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")
CLIENT_ID = "c7feaea8c49046a9b8ecaa0706dd3759"
CLIENT_SECRET = "b85803bd5a0148d3a9098a64e9c10474"
REDIRECT_URI = 'http://localhost:8000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'
CODE_VERIFIER = pkce.generate_code_verifier(length=128)
CODE_CHALLENGE = pkce.get_code_challenge(CODE_VERIFIER)

@app.get('/')
async def index():
    return "please press for service[spotify-login] <a href='/login'> login </a>"

@app.get('/login')
async def login():
    scope = 'user-read-currently-playing user-read-recently-played user-read-private user-read-email playlist-read-private playlist-read-collaborative user-read-recently-played'

    params = {
        'client_id' : CLIENT_ID,
        'response_type' : 'code',
        'scope' : scope,
        'redirect_uri' : REDIRECT_URI,
        'code_challenge_method': 'S256',
        'code_challenge' : CODE_CHALLENGE

    } 

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return RedirectResponse(auth_url)

@app.get('/callback')
async def callback(request: Request):
    session = request.session
    if 'error' in request.query_params:
        return JSONResponse({"error": request.query_params['error']})
    if 'code' in request.query_params:
        req_body = {
            'code': request.query_params['code'],
            'grant_type': 'authorization_code',
            'redirect_uri':REDIRECT_URI,
            'client_id': CLIENT_ID,
            'code_verifier' : CODE_VERIFIER
        }
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return RedirectResponse('/me')

@app.get('/me')
async def get_playlist(request: Request):
    session = request.session
    if 'access_token' not in session:
        return RedirectResponse('login')
    if datetime.now().timestamp() > session['expires_at']:
        return RedirectResponse('/refresh-token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + "me/player/recently-played", headers=headers)
    playlist = response.json()
    return JSONResponse(playlist)

@app.get('/refresh-token')
def refresh_token(request: Request):
    session = request.session
    if 'refresh_token' not in session:
        return RedirectResponse('/login')
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type' : 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return RedirectResponse('/me')
