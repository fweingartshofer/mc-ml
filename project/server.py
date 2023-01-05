from multiprocessing import Queue, Process
from typing import Union

import tekore as tk
import werkzeug
from flask import session, Flask, redirect, request
from tekore import Credentials, RefreshingCredentials, Spotify


class SingleUseAuthServer:
    def __init__(self, host: str,
                 port: int,
                 spotify: Spotify,
                 credentials: Union[Credentials, RefreshingCredentials]):
        self.auths = {}  # Ongoing authorisations: state -> UserAuth
        self.users = {}  # User tokens: state -> token (use state as a user ID)
        self.login_msg = f'You can <a href="/login">login</a>'
        self.host = host
        self.port = port
        self.spotify = spotify
        self.credentials = credentials

    def app_factory(self, queue: Queue) -> Flask:
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'aliens'

        @app.route('/', methods=['GET'])
        def main():
            user = session.get('user', None)
            token = self.users.get(user, None)

            # Return early if no login or old session
            if user is None or token is None:
                session.pop('user', None)
                return f'User ID: None<br>{self.login_msg}'

            page = f'User ID: {user}<br>{self.login_msg}'
            if token.is_expiring:
                token = self.credentials.refresh(token)
                self.users[user] = token

            try:
                with self.spotify.token_as(token):
                    playback = self.spotify.playback_currently_playing()

                item = playback.item.name if playback else None
                page += f'<br>Now playing: {item}'
            except tk.HTTPError:
                page += '<br>Error in retrieving now playing!'

            return page

        @app.route('/login', methods=['GET'])
        def login():
            if 'user' in session:
                return redirect('/', 307)

            scope = [tk.scope.user_top_read, tk.scope.user_read_currently_playing]
            auth = tk.UserAuth(self.credentials, scope)
            self.auths[auth.state] = auth
            return redirect(auth.url, 307)

        @app.route('/callback', methods=['GET'])
        def login_callback():
            code = request.args.get('code', None)
            state = request.args.get('state', None)
            auth = self.auths.pop(state, None)

            if auth is None:
                return 'Invalid state!', 400

            token = auth.request_token(code, state)
            session['user'] = state
            self.users[state] = token
            queue.put(token)
            return "Shutting down..."

        return app

    def run(self, _: str,  queue: Queue):
        application = self.app_factory(queue)
        werkzeug.serving.run_simple(self.host, self.port, application, use_reloader=False)

    def spawn_single_use_server(self) -> tk.Token:
        queue = Queue()
        p = Process(target=self.run, args=("dummy", queue))
        p.start()
        token = queue.get(block=True)
        p.terminate()
        return token
