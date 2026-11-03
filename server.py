import os
from aiohttp import web
import datetime

async def handle_root(request):
    return web.json_response({
        "status": "online",
        "service": "GLOBAL BYPASS Discord Bot",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

async def handle_health(request):
    return web.json_response({"status": "healthy"}, status=200)

async def handle_logo(request):
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        return web.FileResponse(logo_path)
    return web.Response(text="Logo not found", status=404)

def make_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/logo.png", handle_logo)
    return app

async def start_server(port: int = 8080):
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[*] Keep-Alive Web Server started on port {port}")
