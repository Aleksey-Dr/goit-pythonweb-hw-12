FROM python:3.11-slim-buster

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv sync --dev

COPY . /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]