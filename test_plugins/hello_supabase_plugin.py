"""
Hello Supabase Plugin - NeoArch/Aurora Plugin
A tiny test plugin used to verify Supabase Community Plugins upload and install.

Author: Aurora Test
Version: 1.0.0
"""

def _log(app, msg):
    try:
        app.log(msg)
    except Exception:
        print(msg)


def on_startup(app):
    """Called when NeoArch starts up"""
    _log(app, "✅ Hello Supabase Plugin: on_startup called")


def on_tick(app):
    """Called periodically (every ~60 seconds)"""
    _log(app, "⏱️ Hello Supabase Plugin: on_tick heartbeat")


def on_view_changed(app, view_id):
    """Called when user switches between views"""
    _log(app, f"👀 Hello Supabase Plugin: view changed -> {view_id}")

# You can add more helper functions below.
