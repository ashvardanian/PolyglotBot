# PolyglotBot

> Why prompt one model when you can prompt many?

![Polyglot icon](polyglot.png)

Prompt once and receive answers from GPT, Claude, Llama, Mistral and relevant popular bots all at once.
Compare responses, evaluate models, hear opinions from multiple sources, don’t just rely on one.
The system uses 4 models by default and triggers custom models for specific queries, when you ask culinary, psychology, or fitness-related questions.

## Usage

To communicate with bot, please navigate to [poe.com and find the PolyglotBotAI](https://poe.com/PolyglotBotAI).
Alternatively, you can re-create the setup using Modal to serve the stateless backend:

```sh
modal serve main.py
modal deploy main.py # if you are done building and want to ship ;)
```

In case you update the list of available modal, make sure to manually trigger the update on the Quora or Poe side:

```sh
curl -X POST https://api.poe.com/bot/fetch_settings/PolyglotBotAI/$POE_ACCESS_TOKEN
```

The system can use our custom RAG with Wikipedia and Arxiv papers, if provided the backend address:

```sh
curl -L "${WEB_SEARCH_BACKEND}/search?query=Text&top_k=5"
```

## Setup

```sh
conda create -n polyglotbot python=3.10
conda activate polyglotbot
```
