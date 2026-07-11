from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path


def spa(request):
    """Serve the built React app for all non-API routes so client-side
    routing (and page refreshes on deep links) works."""
    index = settings.FRONTEND_DIST_DIR / "index.html"
    if not index.exists():
        raise Http404("Frontend not built. Run `npm run build` in frontend/.")
    return FileResponse(open(index, "rb"))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("gym.urls")),
    # Catch-all: anything that isn't an API/admin/static route gets the SPA.
    re_path(r"^(?!api/|admin/|static/).*$", spa),
]
