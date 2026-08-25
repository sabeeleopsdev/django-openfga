import logging

import inngest
from django.conf import settings

# Dev-server/base-URL selection is controlled entirely via the INNGEST_DEV /
# INNGEST_BASE_URL env vars (see .env), so this client is environment-agnostic
# and needs no code change to point at Inngest Cloud later.
inngest_client = inngest.Inngest(
    app_id=settings.INNGEST_APP_ID,
    logger=logging.getLogger("eventing"),
)
