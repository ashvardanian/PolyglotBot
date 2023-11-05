# PolyglotBot

```sh
modal serve main.py
```

In case you update the list of dependencies:

```sh
curl -X POST https://api.poe.com/bot/fetch_settings/PolyglotBotAI/$POE_ACCESS_TOKEN
```

To access the Retrieval Augmentation API:

```sh
curl -L "${WEB_SEARCH_BACKEND}/search?query=Text&top_k=5"
```

## Setup

```sh
conda create -n polyglotbot python=3.10
conda activate polyglotbot
```
