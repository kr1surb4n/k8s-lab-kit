# A7 PHP image: the official php-fpm image plus the PostgreSQL driver.
#
# SQLite (pdo_sqlite) is already compiled in; pdo_pgsql is not.
# Build from this folder:
#   docker build -t k8s-lab/php:8.3 manifests/a7/php
#
# minikube uses the host's docker daemon with the docker driver, so an image
# built here is visible to the cluster without a registry.
FROM php:8.3-fpm-alpine

# Build tools and headers are needed only while compiling, then removed.
# postgresql-libs is kept: it is the runtime lib that the compiled pdo_pgsql
# links against, and deleting it leaves a broken extension.
RUN apk add --no-cache --virtual .build-deps postgresql-dev \
    && docker-php-ext-install pdo_pgsql \
    && apk del .build-deps \
    && apk add --no-cache postgresql-libs

# Fail loudly instead of serving a page that cannot reach either database.
RUN php -r 'new PDO("sqlite::memory:"); new PDO("pgsql:host=127.0.0.1;port=1", "x", "x");' 2>&1 | grep -qv 'could not find driver' \
    || (echo "pdo_sqlite/pdo_pgsql missing" >&2; exit 1)

# The app is mounted at run time, so the image stays small and reusable.
WORKDIR /var/www/html
