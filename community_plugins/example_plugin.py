"""
Example Plugin - NeoArch Community Plugin
A sample plugin demonstrating NeoArch plugin capabilities

Author: NeoArch Team
Version: 1.0.0
"""

import time
import psutil
import os

def on_startup(app):
    """Called when NeoArch starts"""
    try:
        app.log("🚀 Example Plugin loaded successfully!")
        app.log("📊 This plugin demonstrates basic NeoArch plugin functionality")
        show_system_info(app)
    except Exception as e:
        app.log(f"Example plugin startup error: {e}")

def on_tick(app):
    """Called every 60 seconds"""
    try:
        # Example: Monitor system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        if cpu_percent > 80:
            app.log(f"⚠️ High CPU usage detected: {cpu_percent}%")
        if memory.percent > 85:
            app.log(f"⚠️ High memory usage: {memory.percent}%")

    except Exception as e:
        pass  # Silently handle errors in periodic tasks

def on_view_changed(app, view_id):
    """Called when user switches views"""
    try:
        if view_id == "discover":
            app.log("🔍 User browsing package discovery")
        elif view_id == "updates":
            app.log("⬆️ User checking for updates")
        elif view_id == "plugins":
            app.log("🧩 User browsing plugins")
    except Exception as e:
        pass

def show_system_info(app):
    """Display basic system information"""
    try:
        import platform
        system = platform.system()
        release = platform.release()
        app.log(f"💻 System: {system} {release}")

        # Show CPU info
        cpu_count = psutil.cpu_count()
        app.log(f"🖥️ CPU Cores: {cpu_count}")

        # Show memory info
        memory = psutil.virtual_memory()
        total_gb = round(memory.total / (1024**3), 1)
        app.log(f"🧠 Memory: {total_gb} GB total")

    except Exception as e:
        app.log(f"Could not retrieve system info: {e}")

# Custom functions that can be called by other plugins or manually
def get_system_stats():
    """Return current system statistics"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
    except Exception:
        return {}

def create_backup_reminder(app):
    """Create a backup reminder message"""
    try:
        app.log("💾 Backup Reminder: Consider creating a system backup!")
        app.log("   Go to Settings → Auto Update to enable automatic snapshots")
        return True
    except Exception:
        return False
