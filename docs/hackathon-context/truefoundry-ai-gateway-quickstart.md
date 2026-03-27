# TrueFoundry AI Gateway Quickstart Snapshot

## Source

- URL: https://www.truefoundry.com/docs/ai-gateway/quick-start
- Fetched on: 2026-03-28 (Asia/Tokyo)
- Page title: Quick Start Guide: Setup & Integration - TrueFoundry Docs
- Canonical URL: https://www.truefoundry.com/docs/ai-gateway/quick-start

## Page Summary

This quickstart explains how to set up the TrueFoundry AI Gateway, attach model providers, retrieve the gateway base URL and API key, and call the gateway through OpenAI-compatible clients.

## Main Quickstart Flow

- Sign up for TrueFoundry, verify your email, and land on the main workspace.
- Add your models by selecting a provider and supplying that provider's API key.
- Try the configured models in the Playground.
- Integrate the gateway into application code using the provided base URL and credentials.

## What The Page Emphasizes

- You can add models from a chosen provider after creating a provider account.
- Multiple API keys from the same provider can be added by creating separate provider accounts.
- The page exposes a `Gateway Base URL` that is intended to be used as an OpenAI-compatible base URL.
- Authentication can use either a `Personal Access Token (PAT)` or a `Virtual Account Token (VAT)`.
- The page recommends `VAT` for applications.
- Token creation is described under the `Access` section of the TrueFoundry platform.

## Key Integration Values

- `GATEWAY_BASE_URL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- Example placeholder API key shown on the page: `your_truefoundry_api_key`

## Example Usage Shape

- Python example uses `from openai import OpenAI`.
- The client is initialized with `api_key` and `base_url`.
- The page also shows environment-variable based setup:
  - `export OPENAI_BASE_URL="{GATEWAY_BASE_URL}"`
  - `export OPENAI_API_KEY="your_truefoundry_api_key"`

## SDK / Framework Snippets Mentioned

- OpenAI SDK
- LangChain
- Python (streaming and non-streaming)
- Node.js
- LangGraph
- LlamaIndex
- Google ADK
- cURL

## Page Sections

- Add Provider Account and Models
- Gateway Base URL
- API Key
- Example Usage

## Hackathon Relevance For DeepOps

- This is a strong quick-start reference if we need a unified LLM gateway in front of multiple providers during the hackathon.
- The OpenAI-compatible base URL model reduces integration friction for existing OpenAI SDK code.
- `VAT` plus the gateway URL is likely the cleanest application-facing setup if we wire TrueFoundry into a backend service in this repo.
