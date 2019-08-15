FROM python:alpine
LABEL maintainer="ballouwj@gmail.com"

COPY . ./app

WORKDIR /app
RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

CMD ["python", "-u", "server.py"]