FROM python:alpine
RUN apk add libmagic

RUN pip3 install bs4 pillow mastodon.py feedparser

RUN mkdir /opt/rss2mastodon
RUN mkdir /etc/rss2mastodon
RUN mkdir /var/run/rss2mastodon

COPY rss2mastodon.py /opt/rss2mastodon/rss2mastodon.py
COPY atom2mastodon.py /opt/rss2mastodon/atom2mastodon.py

RUN chown -R 0:0 /opt/rss2mastodon /etc/rss2mastodon  /var/run/rss2mastodon
ENTRYPOINT [ "/bin/sh" ]
