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

