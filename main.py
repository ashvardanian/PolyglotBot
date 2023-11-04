import os

from fastapi_poe import make_app
from modal import Image, Stub, asgi_app

from bot import PolyglotBot

bot = PolyglotBot()

# The following is setup code that is required to host with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")

# Rename "poe-server-bot-quick-start" to your preferred app name.
stub = Stub("PolyglotBotAI")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(
        bot, allow_without_key=True, access_key=os.environ.get("POE_ACCESS_KEY")
    )
    return app
