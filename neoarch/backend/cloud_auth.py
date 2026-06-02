import os
import json
import webbrowser
import threading
import http.server
from urllib.parse import urlparse, parse_qs
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

CONFIG_DIR = Path.home() / ".config" / "neoarch"
SESSION_FILE = CONFIG_DIR / "cloud_session.json"

SUPABASE_URL = "https://fdzeqeobabojnhqiokky.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_YkQx9d5kwC7r2ewA6ZI30g_hYHV5-FU"
WEBSITE_URL = "https://sanjaya-danushka.github.io/Neoarch"

try:
    from supabase import create_client, Client as SupabaseClient
except ImportError:
    SupabaseClient = None


@dataclass
class CloudUser:
    id: str
    email: str
    name: str
    avatar_url: str


class CloudAuthManager(QObject):
    login_changed = pyqtSignal(object)  # CloudUser | None

    def __init__(self):
        super().__init__()
        self._client: Optional[SupabaseClient] = None
        self._user: Optional[CloudUser] = None
        self._httpd: Optional[http.server.HTTPServer] = None
        self._load_session()

    def _load_session(self):
        if not SESSION_FILE.exists():
            return
        try:
            data = json.loads(SESSION_FILE.read_text())
            if SupabaseClient is not None:
                client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                client.auth.set_session(data["access_token"], data["refresh_token"])
                user = client.auth.get_user()
                if user.user:
                    self._client = client
                    self._set_user(user.user)
            else:
                self._set_user(CloudUser(
                    id=data.get("user_id", ""),
                    email=data.get("email", ""),
                    name=data.get("name", ""),
                    avatar_url=data.get("avatar_url", ""),
                ))
        except Exception:
            self._clear_session()

    def _save_session(self, access_token: str, refresh_token: str):
        if not self._user:
            return
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": self._user.id,
            "email": self._user.email,
            "name": self._user.name,
            "avatar_url": self._user.avatar_url,
        }))

    def _clear_session(self):
        self._client = None
        self._user = None
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def _set_user(self, supabase_user):
        metadata = supabase_user.user_metadata or {}
        avatar = (
            metadata.get("avatar_url")
            or metadata.get("picture")
            or metadata.get("avatar")
            or ""
        )
        self._user = CloudUser(
            id=supabase_user.id,
            email=supabase_user.email or "",
            name=metadata.get("full_name") or metadata.get("name") or supabase_user.email or "User",
            avatar_url=avatar,
        )
        self.login_changed.emit(self._user)

    @property
    def user(self) -> Optional[CloudUser]:
        return self._user

    @property
    def is_logged_in(self) -> bool:
        return self._user is not None

    @property
    def client(self) -> Optional[SupabaseClient]:
        return self._client

    def start_login(self):
        port = self._find_free_port()
        self._start_local_server(port)
        callback_url = f"http://127.0.0.1:{port}/callback"
        login_url = f"{WEBSITE_URL}/login?callback={callback_url}"
        webbrowser.open(login_url)

    def logout(self):
        if self._client:
            try:
                self._client.auth.sign_out()
            except Exception:
                pass
        self._clear_session()
        self._user = None
        self.login_changed.emit(None)

    def _find_free_port(self) -> int:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _start_local_server(self, port: int):
        manager = self

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                access_token = params.get("access_token", [None])[0]
                refresh_token = params.get("refresh_token", [None])[0]

                if access_token and refresh_token:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><p>Signed in! You can close this window.</p><script>window.close()</script></body></html>")
                    threading.Thread(target=manager._handle_tokens, args=(access_token, refresh_token), daemon=True).start()
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing tokens")

            def log_message(self, *a, **kw):
                pass

        self._httpd = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def _handle_tokens(self, access_token: str, refresh_token: str):
        if SupabaseClient is None:
            self._user = CloudUser(id="", email="", name="User", avatar_url="")
            self._save_session(access_token, refresh_token)
            self.login_changed.emit(self._user)
            return

        try:
            client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            client.auth.set_session(access_token, refresh_token)
            user = client.auth.get_user()
            if user.user:
                self._client = client
                self._set_user(user.user)
                self._save_session(access_token, refresh_token)
        except Exception as e:
            print(f"Cloud auth error: {e}")

        if self._httpd:
            threading.Thread(target=self._httpd.shutdown, daemon=True).start()
            self._httpd = None

    def get_favorites(self) -> list:
        if not self._client or not self._user:
            return []
        try:
            data = self._client.table("user_favorites") \
                .select("bundle_data") \
                .eq("user_id", self._user.id) \
                .order("created_at", ascending=False) \
                .limit(1) \
                .execute()
            if data.data and len(data.data) > 0:
                return data.data[0].get("bundle_data", [])
        except Exception:
            pass
        return []

    def save_favorites(self, bundle_name: str, bundle_data: list) -> bool:
        if not self._client or not self._user:
            return False
        try:
            self._client.table("user_favorites").upsert({
                "user_id": self._user.id,
                "bundle_name": bundle_name,
                "bundle_data": bundle_data,
                "item_count": len(bundle_data),
            }).execute()
            return True
        except Exception as e:
            print(f"Save favorites error: {e}")
            return False

    def delete_all_favorites(self) -> bool:
        if not self._client or not self._user:
            return False
        try:
            self._client.table("user_favorites") \
                .delete() \
                .eq("user_id", self._user.id) \
                .execute()
            return True
        except Exception:
            return False
