FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl nodejs npm && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install uv
RUN uv sync

RUN uv run reflex init
RUN uv run reflex export --no-zip

EXPOSE 3000
EXPOSE 8000

CMD ["uv", "run", "reflex", "run", "--env", "prod"]