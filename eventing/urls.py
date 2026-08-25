import inngest.django

from eventing.client import inngest_client
from eventing.functions import handle_db_change

# inngest.django.serve() returns a ready-made URLPattern (already wrapped in
# django.urls.path), so it's included directly rather than via path(..., view).
urlpatterns = [
    inngest.django.serve(inngest_client, [handle_db_change]),
]
