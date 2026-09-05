import json
import base64
import webbrowser
import threading
import http.server
from urllib.parse import urlparse, parse_qs
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from time import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

CONFIG_DIR = Path.home() / ".config" / "neoarch"
SESSION_FILE = CONFIG_DIR / "cloud_session.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

SUPABASE_URL = "https://rlbwkihgijdlqvyeycjj.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_IlIXtZ8W3lnrkGli9TXVRA_XrrzIOPH"

# Default — overridden at runtime if cloud_website_url is in settings.json
DEFAULT_WEBSITE_URL = "https://neoarch.dpdns.org"

try:
    from supabase import create_client, ClientOptions, Client as SupabaseClient
except ImportError:
    SupabaseClient = None


def _website_url() -> str:
    try:
        if SETTINGS_FILE.exists():
            s = json.loads(SETTINGS_FILE.read_text())
            return s.get("cloud_website_url", "") or DEFAULT_WEBSITE_URL
    except Exception:
        pass
    return DEFAULT_WEBSITE_URL


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification (local convenience)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        pad = 4 - len(payload) % 4
        payload += "=" * pad
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


@dataclass
class CloudUser:
    id: str       # Clerk subject, e.g. "user_2xxx"
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

    # ── Session persistence ─────────────────────────────────────────

    def _load_session(self):
        if not SESSION_FILE.exists():
            return
        try:
            data = json.loads(SESSION_FILE.read_text())
            token = data.get("token", "")
            claims = _decode_jwt_payload(token)
            exp = claims.get("exp", 0)
            if exp and exp < time():
                self._clear_session()
                return
            self._set_user_from_data(data)
            self._client = self._make_client(token)
        except Exception:
            self._clear_session()

    def _save_session(self, token: str):
        if not self._user:
            return
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps({
            "token": token,
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

    def _set_user_from_data(self, data: dict):
        self._user = CloudUser(
            id=data.get("user_id", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url", ""),
        )
        self.login_changed.emit(self._user)

    # ── Auth flow ───────────────────────────────────────────────────

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
        login_url = f"{_website_url()}/sign-in?callback={callback_url}"
        webbrowser.open(login_url)

    def logout(self):
        self._clear_session()
        self.login_changed.emit(None)

    # ── Local callback server ───────────────────────────────────────

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
                token = params.get("token", [None])[0]
                user_id = params.get("user_id", [None])[0]
                email = params.get("email", [None])[0]
                name = params.get("name", [None])[0]
                avatar_url = params.get("avatar_url", [None])[0]

                if token and user_id:
                    homepage = json.dumps(f"{_website_url()}/")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write((
                        "<!DOCTYPE html>\n"
                        "<html>\n"
                        '<head><meta charset="utf-8"><title>Signed In - NeoArch</title></head>\n'
                        '<body style="margin:0;display:flex;align-items:center;justify-content:center;\n'
                        '             min-height:100vh;background:#0F1117;color:#fff;font-family:system-ui">\n'
                        '<div style="text-align:center"><h1>NeoArch</h1>'
                        "<p>Signed in! <strong>Taking you back to the site...</strong></p></div>\n"
                        "<script>\n"
                        f"  window.location.replace({homepage});\n"
                        "  setTimeout(function(){ window.close(); }, 1500);\n"
                        "</script>\n"
                        "</body></html>\n"
                    ).encode("utf-8"))
                    threading.Thread(
                        target=manager._handle_token,
                        args=(token, user_id, email, name, avatar_url),
                        daemon=True,
                    ).start()
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing token")

            def log_message(self, *a, **kw):
                pass

        self._httpd = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def _handle_token(self, token: str, user_id: str = "", email: str = "", name: str = "", avatar_url: str = ""):
        """Receive Clerk JWT + user info from the browser redirect, build client."""
        try:
            claims = _decode_jwt_payload(token)
            sub = claims.get("sub") or user_id
            if not sub:
                print("cloud_auth: JWT missing sub claim")
                return

            self._user = CloudUser(
                id=sub,
                email=email or claims.get("email") or "",
                name=name or claims.get("name") or email or sub,
                avatar_url=avatar_url or claims.get("avatar_url") or "",
            )
            self._client = self._make_client(token)
            self._save_session(token)
            self.login_changed.emit(self._user)
        except Exception as e:
            print(f"cloud_auth error: {e}")
        finally:
            if self._httpd:
                threading.Thread(target=self._httpd.shutdown, daemon=True).start()
                self._httpd = None

    # ── Supabase client (Clerk JWT as Bearer) ───────────────────────

    @staticmethod
    def _make_client(token: str) -> Optional[SupabaseClient]:
        if SupabaseClient is None:
            return None
        return create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(
                headers={"Authorization": f"Bearer {token}"},
                auto_refresh_token=False,
                persist_session=False,
            ),
        )

    # ── Cloud bundle operations ─────────────────────────────────────

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

    def save_bundle_to_cloud(self, bundle_key: str, bundle_name: str, items: list) -> bool:
        if not self._client or not self._user:
            return False
        try:
            existing = self._client.table("user_bundles") \
                .select("id") \
                .eq("user_id", self._user.id) \
                .eq("bundle_key", bundle_key) \
                .limit(1) \
                .execute()
            row = {
                "user_id": self._user.id,
                "bundle_key": bundle_key,
                "bundle_name": bundle_name,
                "bundle_data": items,
                "item_count": len(items),
            }
            if existing.data:
                self._client.table("user_bundles") \
                    .update(row) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                self._client.table("user_bundles").insert(row).execute()
            return True
        except Exception as e:
            print(f"save_bundle_to_cloud error: {e}")
            return False

    def load_bundle_from_cloud(self, bundle_key: str) -> list:
        if not self._client or not self._user:
            return []
        try:
            resp = self._client.table("user_bundles") \
                .select("bundle_data") \
                .eq("user_id", self._user.id) \
                .eq("bundle_key", bundle_key) \
                .limit(1) \
                .execute()
            if resp.data:
                raw = resp.data[0].get("bundle_data", [])
                return raw if isinstance(raw, list) else []
        except Exception:
            pass
        return []

    def list_cloud_bundles(self) -> list:
        if not self._client or not self._user:
            return []
        try:
            resp = self._client.table("user_bundles") \
                .select("bundle_key, bundle_name, item_count") \
                .eq("user_id", self._user.id) \
                .order("bundle_name") \
                .execute()
            return [
                {"key": r["bundle_key"], "name": r["bundle_name"], "count": r["item_count"]}
                for r in (resp.data or [])
            ]
        except Exception:
            return []

    def delete_bundle_from_cloud(self, bundle_key: str) -> bool:
        if not self._client or not self._user:
            return False
        try:
            self._client.table("user_bundles") \
                .delete() \
                .eq("user_id", self._user.id) \
                .eq("bundle_key", bundle_key) \
                .execute()
            return True
        except Exception:
            return False

    def generate_share_code(self, bundle_name: str, items: list) -> str:
        if not self._client or not self._user:
            return ""
        try:
            import hashlib, time
            raw = f"{self._user.id}:{bundle_name}:{time.time()}"
            code = hashlib.sha256(raw.encode()).hexdigest()[:8]
            self._client.table("shared_bundles").insert({
                "share_code": code,
                "creator_id": self._user.id,
                "bundle_name": bundle_name,
                "bundle_data": items,
                "item_count": len(items),
            }).execute()
            return code
        except Exception as e:
            print(f"generate_share_code error: {e}")
            return ""

    def get_shared_bundle(self, code: str) -> dict:
        if not self._client:
            # Allow anonymous reads with anon key + no bearer
            anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            client = anon
        else:
            client = self._client
        try:
            resp = client.table("shared_bundles") \
                .select("bundle_name, bundle_data") \
                .eq("share_code", code.strip()) \
                .limit(1) \
                .execute()
            if resp.data:
                r = resp.data[0]
                data = r.get("bundle_data", [])
                return {"name": r.get("bundle_name", "Shared"), "items": data if isinstance(data, list) else []}
        except Exception:
            pass
        return {}
