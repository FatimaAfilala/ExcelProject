FROM python:3.9-slim-buster

WORKDIR /usr/src/app

RUN apt-get update -q
RUN apt-get install curl git -qy
RUN curl https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh > install-git-lfs.sh
RUN bash install-git-lfs.sh
RUN apt-get install git-lfs -qy

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY . .

RUN git-lfs pull
RUN python -m pip install -r requirements.txt

CMD [ "bash", "run-farc.sh"]

EXPOSE 8080