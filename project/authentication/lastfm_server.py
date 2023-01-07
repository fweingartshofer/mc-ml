import os
from hashlib import md5
from multiprocessing import Queue, Process

import pylast
import werkzeug
from flask import Flask, session, request, redirect

from project.authentication import lastfm_api_key_var, lastfm_shared_secret_var, lastfm_auth_url


class LastFmCredentials:
    api_key: str
    shared_secret: str

    def __init__(self, api_key=None, shared_secret=None):
        if api_key is None:
            self.api_key = os.environ.get(lastfm_api_key_var)
        else:
            self.api_key = api_key

        if shared_secret is None:
            self.shared_secret = os.environ.get(lastfm_shared_secret_var)
        else:
            self.shared_secret = api_key


class LastFmServer:
    def __init__(self, host: str,
                 port: int,
                 credentials: LastFmCredentials):
        self.users = {}  # User tokens: state -> token (use state as a user ID)
        self.login_msg = f'You can <a href="/login">login</a>'
        self.host = host
        self.port = port
        self.credentials = credentials

    def app_factory(self, queue: Queue) -> Flask:
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'aliens'

        @app.route('/', methods=['GET'])
        def main():
            user = session.get('user', None)
            if user is None:
                return self.login_msg
            page = f'User ID: {user}<br>{self.login_msg}'
            return page

        @app.route('/login', methods=['GET'])
        def login():
            if 'user' in session:
                return redirect('/', 307)
            return redirect(
                f"{lastfm_auth_url}?api_key={self.credentials.api_key}&cb=http://{self.host}:{self.port}/callback",
                307
            )

        @app.route('/callback', methods=['GET'])
        def login_callback():
            token = request.args.get('token', None)

            session['user'] = token
            self.users[token] = token
            queue.put(token)
            return "Shutting down..."

        return app

    def run(self, _: str, queue: Queue):
        application = self.app_factory(queue)
        werkzeug.serving.run_simple(self.host, self.port, application, use_reloader=False)

    def _create_api_signature(self, token: str):
        signature = f"api_key{self.credentials.api_key}methodauth.getSessiontoken{token}{self.credentials.shared_secret}"
        return str(md5(signature))

    def spawn_single_use_server(self) -> str:
        queue = Queue()
        p = Process(target=self.run, args=("dummy", queue))
        p.start()
        token = queue.get(block=True)
        signature = self._create_api_signature(token)
        # TODO: request session token
        p.terminate()
        return token
