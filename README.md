# RAG Lab

Small educational Retrieval-Augmented Generation lab built step by step.

The goal is to understand each internal stage before adding frameworks or external services.

Current stages:

1. Prepare the lab.
2. Create a fictitious knowledge document.
3. Read the document from Python.
4. Split the document into simple character-based chunks.

## Setup

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

At this stage there are no external dependencies.

## Run

Read the source document:

```bash
python src/read_document.py
```

Run the first chunking experiment:

```bash
python src/chunk_document.py
```
