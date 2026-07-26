from backend.main import app
print("App loaded OK")
print("Routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}")
