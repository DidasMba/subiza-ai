# Subiza AI

Subiza AI is a RAG-powered customer support chat agent for small businesses, built on Gemini with the [Google Gen AI SDK](https://github.com/googleapis/python-genai) and running on Gemini Enterprise Agent Platform (formerly Vertex AI). Give it your FAQs, hours, prices and policies, and it answers customer questions grounded only in that knowledge — with a clear handoff to a human when it doesn't know.

*Subiza* means "answer" in Kinyarwanda. Built for pharmacies and other local businesses, and usable by any small business.

## What it does

- Loads a business's FAQ/knowledge from `app/knowledge/business_faq.md`
- Embeds it with Gemini's embedding model, retrieves relevant chunks per question
- Answers customer questions grounded ONLY in that knowledge (no hallucinated policies)
- Replies in the customer's language, whatever language the FAQ is written in
  (measured in French, English and Swahili, see below)
- Falls back to "a human will follow up" when it doesn't know — critical for trust
- Understands follow-up questions ("and on Sunday?") using the recent conversation
- Ships with a polished, mobile-friendly chat widget (light/dark mode, suggested
  questions, source chips, clear handoff notices) so you can demo it today

## Quickstart (5 minutes)

```bash
git clone https://github.com/DidasMba/subiza-ai.git
cd subiza-ai
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then pick a backend in `.env`:

- **Gemini Enterprise Agent Platform (recommended).** Set `GOOGLE_CLOUD_PROJECT` to a project with the Agent Platform API (`aiplatform.googleapis.com`) enabled, then run `gcloud auth application-default login` once. No API key is involved.
- **Gemini Developer API.** Leave `GOOGLE_CLOUD_PROJECT` unset and set `GEMINI_API_KEY` to a free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
uvicorn app.main:app --reload
```

The startup log says which backend is in use. Open http://localhost:8000 and try: "What time do you open?" It answers using the included fictional pharmacy example.

## Multilingual demo: a pharmacy in Bukavu

The demo shown at DevFest Kivu 2026 runs the same code on a French FAQ for a fictional pharmacy in Bukavu, DR Congo. Customers can ask in French, Swahili or English, and the agent answers in the language of the question.

Add these lines to `.env`:

```bash
KB_PATH=app/knowledge/pharmacie_bukavu.md
BUSINESS_NAME="Pharmacie Mfano (démo)"
UI_LANGUAGE=fr
CHAT_MODEL=gemini-3.5-flash-lite
SUGGESTED_QUESTIONS="Vous êtes ouverts le dimanche ?|Vous livrez à Kadutu ?|Je peux payer avec M-Pesa ?|Combien coûte un test de glycémie ?"
```

*Mfano* means "example" in Swahili: the pharmacy, its address and its phone number are made up. `UI_LANGUAGE` sets the language of the widget and of the two fixed replies (`en` or `fr`). Gemini's own answers always follow the customer.

### How it stays safe in every language

- **Structured output.** Gemini returns JSON with three fields, in this order: `language` (of the question), `reply` (written in that language) and `handoff`. Naming the language first stops a small model from drifting into the language of the FAQ.
- **The model flags the handoff.** An earlier version looked for English words such as "pharmacist" in the reply, so a Swahili reply that sent the customer to the pharmacist never showed the handoff notice. The `handoff` field works in any language.
- **No medical advice.** Questions about dosage, interactions or symptoms are sent to the on-duty pharmacist: a hard rule in the prompt, checked by the eval below.
- **No false "no".** When the FAQ doesn't mention a product, the agent says a team member will check instead of saying the pharmacy doesn't have it.
- **Overload.** When Gemini answers 503 ("high demand"), the question gets one more try after a second. Any other failure gets the "busy" reply.

### Measured results

Run on 23 November 2026 with `gemini-embedding-001` and `gemini-3.5-flash-lite` on the free Gemini Developer API, against 39 test questions written by the author ([`evals/multilingual_cases.csv`](evals/multilingual_cases.csv)).

| Check | French | English | Swahili |
| --- | --- | --- | --- |
| Right FAQ section ranked first | 9/9 | 9/9 | 8/9 |
| Medical question handed to the pharmacist | 3/3 | 3/3 | 3/3 |
| Medical reply giving a dose | 0/3 | 0/3 | 0/3 |
| Medical reply in the question's language | 3/3 | 2/3 | 3/3 |

The one retrieval miss (Swahili: "can I get my blood pressure checked?") ranked *Prix* first, which also lists the free blood pressure check, and the expected *Services* second; both reach Gemini. One English medical question got its answer in French. The off-topic questions (car tyres) could not be scored: Gemini returned 503 or 504 on all three during the run.

Two findings shaped the design:

- **The similarity floor filters nothing.** Right answers scored 0.66–0.79, but a question about car tyres still scored 0.57–0.65, far above `MIN_SCORE=0.3`. The real guardrail is the model and its `handoff` field, which is why both are tested.
- **Flash-Lite for speed.** One short answer, timed from Kigali on the free tier (18 November 2026, single run): `gemini-3.6-flash` took 33 s, `gemini-3.8-flash` hit the 60 s limit and `gemini-3.5-flash-lite` took 1.6 s. Answering from a short FAQ doesn't need the larger model.

Reproduce them:

```bash
python -m evals.run_eval --retrieval-only           # search only, a few embedding calls
python -m evals.run_eval --kinds medical,off_topic  # full answers, about 3 minutes on the free tier
python check_models.py                              # chat model latency
```

Each run writes every question and reply to `evals/results/` (git-ignored). Read the medical replies yourself.

### Add your language

Lingala, Mashi, Kinyarwanda and every other language are welcome. Add rows to `evals/multilingual_cases.csv` with your language code, run the eval, and open a pull request with the results table.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/chat` | `{"message": "...", "history": [{"role": "user", "content": "..."}]}` → `{"reply", "handed_off", "sources"}` |
| `GET` | `/info` | Business name, suggested questions and texts for the widget |
| `GET` | `/health` | Liveness check |
| `GET` | `/docs` | Interactive OpenAPI docs |

The server is stateless: the widget sends recent turns as `history`, so it scales out on Cloud Run without a session store.

## Configuration

Every setting in `app/config.py` can be overridden with an environment variable (or a line in `.env`), e.g. `BUSINESS_NAME`, `CHAT_MODEL`, `TOP_K`, `MIN_SCORE`, `MAX_HISTORY_TURNS`. See `.env.example`.

On Agent Platform, `GOOGLE_CLOUD_LOCATION` defaults to `global`. If your embedding model isn't served there, set `EMBEDDING_LOCATION` (for example `us-central1`) and the app uses a second client for embeddings only.

All Gemini calls live in `app/gemini.py`. Startup indexing retries up to 3 times. A live customer question gets the "busy" reply after `GEMINI_TIMEOUT` seconds; the only retry is a single quick one when Gemini answers 503 ("high demand"). `THINKING_LEVEL` (default `low`) keeps Gemini from reasoning past that limit; answering from a short FAQ needs little reasoning.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
python -m pytest        # no API key needed — Gemini is replaced with fakes
```

## Use it for your own business

Replace the placeholder content in `app/knowledge/business_faq.md` with your own business's real hours, prices and policies, or point `KB_PATH` to your own file. This is the single highest-leverage thing you can do — the whole quality of the agent depends on this file.

Keep real business data out of version control: if you fork this repo for a real deployment, put your knowledge file somewhere git-ignored (or in a private repo) rather than committing it here.

## Deploy to Cloud Run

On Cloud Run the service's own identity calls Gemini, so there is no API key to store, rotate or leak. Give the service a dedicated service account that can call models and nothing else:

```bash
PROJECT_ID=your-gcp-project-id
gcloud services enable aiplatform.googleapis.com run.googleapis.com --project $PROJECT_ID

gcloud iam service-accounts create support-agent --project $PROJECT_ID
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member "serviceAccount:support-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role roles/aiplatform.user

gcloud run deploy subiza-ai \
  --source . \
  --project $PROJECT_ID \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account support-agent@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global
```

If you deploy with the Gemini Developer API instead, store `GEMINI_API_KEY` in Secret Manager and pass it with `--set-secrets`, never `--set-env-vars`.

## Roadmap

1. **v1 (this repo):** web widget + RAG + Gemini + structured handoff — get one real business using it
2. **WhatsApp integration:** swap the web widget for the WhatsApp Business Cloud API (Meta) as the customer-facing channel — same `/chat` backend
3. **Real handoff:** when the agent hands off, notify a human via email/Slack/WhatsApp and let them reply through the same thread
4. **Agent framework (ADK):** turn the single Gemini call into a proper agent with tools — e.g., "check order status," "log a complaint," "escalate to human" as callable tools instead of prompt tricks
5. **Vector DB upgrade:** once you support multiple businesses or large catalogs, move from in-memory vectors to Vector Search on Gemini Enterprise Agent Platform or AlloyDB + pgvector
6. **Document ingestion:** add Document AI / Gemini multimodal to handle receipts, price lists, or catalogs as PDFs/photos instead of manually written markdown

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the issues labeled `good first issue`.

## License

Apache 2.0. See [LICENSE](LICENSE).
