FROM python:3.12-slim

WORKDIR /srv

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir fastapi==0.143.0 uvicorn==0.54.0 \
    pydantic==2.14.1 starlette==1.9.0 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY main.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "asyncio", "--http", "h11", "--no-access-log"]
