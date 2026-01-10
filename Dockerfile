FROM python:3.11-slim

WORKDIR /app

# pip but faster
RUN pip install uv

COPY app/requirements.txt requirements.txt

RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY app .

CMD ["python", "main.py", "parse_feed", "ner"]
