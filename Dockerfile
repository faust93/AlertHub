# Web
FROM node:lts-alpine as builder_node

WORKDIR /web

COPY ./web /web

RUN npm install \
    && npm run build \
    && ls /web/dist

# Backend
FROM python:3.12-alpine

WORKDIR /alerthub

COPY --from=builder_node /web/dist /alerthub/dist
COPY requirements.txt /alerthub
COPY utils /alerthub/utils
COPY migrations /alerthub/migrations
COPY server.py /alerthub
COPY config.py /alerthub

RUN pip install -r /alerthub/requirements.txt \
    && chmod +x /alerthub/server.py

ENTRYPOINT ["/alerthub/server.py"]
CMD [""]
