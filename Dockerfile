FROM python:3.9-slim-buster

WORKDIR /usr/src/app

COPY . .

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv $VIRTUAL_ENV \
    && python -m pip install -r requirements.txt

CMD [ "bash", "run-farc.sh"]

EXPOSE 8080