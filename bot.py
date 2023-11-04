"""

Sample bot that returns interleaved results from GPT-3.5-Turbo and Claude-instant.

"""
from __future__ import annotations

import json
import asyncio
import re
from collections import defaultdict
from typing import AsyncIterable, AsyncIterator
from copy import deepcopy

from fastapi_poe import PoeBot
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    MetaResponse,
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)


async def combine_streams(
    *streams: AsyncIterator[PartialResponse],
) -> AsyncIterator[PartialResponse]:
    """Combines a list of streams into one single response stream.

    Allows you to render multiple responses in parallel.

    """
    active_streams = {id(stream): stream for stream in streams}
    responses: dict[int, list[str]] = defaultdict(list)

    async def _advance_stream(
        stream_id: int, gen: AsyncIterator[PartialResponse]
    ) -> tuple[int, PartialResponse | None]:
        try:
            return stream_id, await gen.__anext__()
        except StopAsyncIteration:
            return stream_id, None

    while active_streams:
        for coro in asyncio.as_completed(
            [
                _advance_stream(stream_id, gen)
                for stream_id, gen in active_streams.items()
            ]
        ):
            stream_id, msg = await coro
            if msg is None:
                del active_streams[stream_id]
                continue

            if isinstance(msg, MetaResponse):
                continue
            elif msg.is_suggested_reply:
                yield msg
                continue
            elif msg.is_replace_response:
                responses[stream_id] = [msg.text]
            else:
                responses[stream_id].append(msg.text)

            text = "\n\n".join(
                "".join(chunks) for stream_id, chunks in responses.items()
            )
            yield PartialResponse(text=text, is_replace_response=True)


def preprocess_message(message: ProtocolMessage, bot: str) -> ProtocolMessage:
    """Process bot responses to keep only the parts that come from the given bot."""
    if message.role == "bot":
        parts = re.split(r"\*\*([A-Za-z_\-\d]+)\*\* says:\n", message.content)
        for message_bot, text in zip(parts[1::2], parts[2::2]):
            if message_bot.casefold() == bot.casefold():
                return message.model_copy(update={"content": text})
        # If we can't find a message by this bot, just return the original message
        return message
    else:
        return message


def preprocess_query(request: QueryRequest, bot: str) -> QueryRequest:
    """Parses the two bot responses and keeps the one for the current bot."""
    new_query = request.model_copy(
        update={
            "query": [preprocess_message(message, bot) for message in request.query]
        }
    )
    return new_query


async def stream_request_wrapper(
    request: QueryRequest, bot: str, name: bool = True
) -> AsyncIterator[PartialResponse]:
    """Wraps stream_request and labels the bot response with the bot name."""
    if name:
        label = PartialResponse(text=f"**{bot.title()}** says:\n", is_replace_response=True)
        yield label
    async for msg in stream_request(
        preprocess_query(request, bot), bot, request.access_key
    ):
        if isinstance(msg, Exception):
            yield PartialResponse(
                text=f"**{bot.title()}** ran into an error", is_replace_response=True
            )
            return
        elif msg.is_replace_response:
            yield label
        # Force replace response to False since we are already explicitly handling that case above.
        yield msg.model_copy(update={"is_replace_response": False})


class PolyglotBot(PoeBot):
    POPULAR_BOTS = ["GPT-4", "Claude-2-100k", "fw-mistral-7b", "Llama-2-70b"]
    OPTIONAL_BOTS = [
        "PsychologistGPT",
        "leocooks",
        "GrandmaGPT",
        "1FitCoach",
    ]

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:

        bots_to_invoke = PolyglotBot.POPULAR_BOTS.copy() 

        request_plain = "".join(q.content for q in request.query)
        request_plain = request_plain.replace("\n", " ")

        metadata_request = deepcopy(request)
        metadata_request_message = '''
            I'm going to show you a textual request:

            > {request_plain}

            Please evaluate, if you need to use the internet to answer this question.
            And if the question is related to any of the following topics:
                - psychology
                - education
                - cooking
                - fitness

            Provide me the response as a single valid JSON object with the following keys and boolean values:
                - is_related_to_psychology
                - is_related_to_education
                - is_related_to_cooking
                - is_related_to_fitness
                - requires_internet

            Example:

            {{
                "is_related_to_psychology": false,
                "is_related_to_education": true,
                "is_related_to_cooking": false,
                "is_related_to_fitness": false,
                "requires_internet": true,
            }}
            '''.format(
            request_plain=request_plain
        )
        metadata_request.query.clear()
        metadata_request.query.append(
            ProtocolMessage(role="bot", content=metadata_request_message)
        )
        metadata_stream = stream_request_wrapper(metadata_request, "GPT-4", name=False)

        # Parse the GPT's response
        metadata_response = "".join([msg.text async for msg in metadata_stream])
        metadata_response = metadata_response[metadata_response.find("{"):]
        metadata_response = metadata_response[:metadata_response.find("}")+1]
        try:
            metadata = json.loads(metadata_response)
        except json.JSONDecodeError:
            print("Received invalid metadata response from GPT-4", metadata_response)
            metadata = {}
        print("Received metadata response from GPT-4", metadata)

        if metadata["is_related_to_psychology"]:
            bots_to_invoke.append("PsychologistGPT")
        if metadata["is_related_to_cooking"]:
            bots_to_invoke.append("leocooks")
        if metadata["is_related_to_fitness"]:
            bots_to_invoke.append("1FitCoach")

        # This capability is not available for now:
        # if metadata["requires_internet"]:
        #     bots_to_invoke.append("Web-Search")

        streams = [stream_request_wrapper(request, bot) for bot in bots_to_invoke]
        async for msg in combine_streams(*streams):
            yield msg

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        # Only up to 10 dependencies are allowed.
        deps = [*PolyglotBot.POPULAR_BOTS, *PolyglotBot.OPTIONAL_BOTS, "Web-Search"]
        deps = {k: 1 for k in deps}
        deps["GPT-4"] = 2
        return SettingsResponse(server_bot_dependencies=deps)
