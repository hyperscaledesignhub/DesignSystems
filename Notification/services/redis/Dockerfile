FROM redis:7-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 7847

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]