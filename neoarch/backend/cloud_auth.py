import os
import json
import webbrowser
import threading
import http.server
from urllib.parse import urlparse, parse_qs
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

CONFIG_DIR = Path.home() / ".config" / "neoarch"
SESSION_FILE = CONFIG_DIR / "cloud_session.json"

SUPABASE_URL = "https://rlbwkihgijdlqvyeycjj.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_IlIXtZ8W3lnrkGli9TXVRA_XrrzIOPH"
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
        QTimer.singleShot(0, self._load_session)

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
                    self.wfile.write(b"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Signed In - NeoArch</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0F1117;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif;
    overflow: hidden;
  }
  .bubbles {
    position: fixed;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 0;
  }
  .bubble {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(0,191,174,0.1);
    background: rgba(0,191,174,0.05);
    backdrop-filter: blur(64px);
  }
  .b1 { width: 288px; height: 288px; left: -80px; top: 160px; animation: float 6s ease-in-out infinite; }
  .b2 { width: 384px; height: 384px; right: -40px; top: 80px; animation: float-slow 12s ease-in-out infinite; }
  .b3 { width: 192px; height: 192px; bottom: 80px; left: 33%; animation: float 6s ease-in-out infinite; animation-delay: 2s; }
  .card {
    position: relative;
    z-index: 1;
    background: rgba(26,28,37,0.8);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(42,45,58,0.5);
    border-radius: 16px;
    padding: 48px 40px;
    text-align: center;
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
    max-width: 360px;
    width: 90%;
  }
  .logo {
    width: 64px;
    height: 64px;
    margin: 0 auto 16px;
    display: block;
    border-radius: 16px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.1);
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 4px;
    background: linear-gradient(to right, #60a5fa, #22d3ee, #3b82f6);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    background-size: 200% 200%;
    animation: shimmer 4s ease-in-out infinite;
  }
  .check {
    width: 48px;
    height: 48px;
    margin: 24px auto 16px;
    background: linear-gradient(135deg, #60a5fa, #22d3ee, #3b82f6);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 32px rgba(0,191,174,0.2);
  }
  .check svg {
    width: 24px;
    height: 24px;
    stroke: #0F1117;
    stroke-width: 2.5;
    fill: none;
  }
  p {
    color: #8B8FA3;
    font-size: 14px;
    line-height: 1.5;
  }
  p strong {
    color: #F0F0F0;
    font-weight: 600;
  }
  @keyframes float {
    0%, 100% { transform: translateY(0) scale(1); }
    50% { transform: translateY(-30px) scale(1.05); }
  }
  @keyframes float-slow {
    0%, 100% { transform: translateY(0) scale(1) rotate(0deg); }
    33% { transform: translateY(-20px) scale(1.02) rotate(1deg); }
    66% { transform: translateY(10px) scale(0.98) rotate(-1deg); }
  }
  @keyframes shimmer {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
</style>
</head>
<body>
<div class="bubbles">
  <div class="bubble b1"></div>
  <div class="bubble b2"></div>
  <div class="bubble b3"></div>
</div>
<div class="card">
  <svg class="logo" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" rx="20" fill="url(#g)"/>
    <path d="M30 50 L45 65 L70 35" stroke="#0F1117" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="100" y2="100">
        <stop stop-color="#60a5fa"/>
        <stop offset="0.5" stop-color="#22d3ee"/>
        <stop offset="1" stop-color="#3b82f6"/>
      </linearGradient>
    </defs>
  </svg>
  <h1>NeoArch</h1>
  <div class="check">
    <svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
  </div>
  <p>Signed in! <strong>You can close this window.</strong></p>
</div>
<script>window.close()</script>
</body>
</html>""")
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
            resp = self._client.table("user_favorites") \
                .select("bundle_data") \
                .eq("user_id", self._user.id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            if resp.data and len(resp.data) > 0:
                raw = resp.data[0].get("bundle_data", [])
                if isinstance(raw, str):
                    return json.loads(raw)
                return raw
        except Exception:
            pass
        return []

    def save_favorites(self, bundle_name: str, bundle_data: list) -> bool:
        if not self._client or not self._user:
            return False
        try:
            self._client.table("user_favorites") \
                .delete() \
                .eq("user_id", self._user.id) \
                .execute()
            self._client.table("user_favorites").insert({
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
