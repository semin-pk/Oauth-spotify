import requests
import pkce
import urllib.parse
from flask import Flask
from flask import request, session
from flask import redirect, jsonify
from datetime import datetime, timedelta
app = Flask(__name__)
app.secret_key = '53d355f8-571a-4590-a310-1f9579440851'

CLIENT_ID = "c7feaea8c49046a9b8ecaa0706dd3759"
CLIENT_SECRET = "b85803bd5a0148d3a9098a64e9c10474"
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'
CODE_VERIFIER = pkce.generate_code_verifier(length=128)
CODE_CHALLENGE = pkce.get_code_challenge(CODE_VERIFIER)
@app.route('/')
def index():
    return "Welcome to my spotify app <a href='/login'>Login with Spotify</a>"

@app.route('/login')
def login():
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

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
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

    return redirect('/me')

@app.route('/me')
def get_playlist():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL + "me/player/recently-played", headers=headers)
    if response:
        playlists = response.json()
    else:
        return "response is Empty"


    return jsonify(playlists)

@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
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

        return redirect('/me')
    
if __name__ == '__main__':
    app.run(host='127.0.0.1', debug = True)