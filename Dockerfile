FROM python:3.13.3 as python-django
WORKDIR /app

# fga CLI: transforms authz/model.fga (DSL) into the JSON shape OpenFGA's
# API expects. Used by `manage.py setup_openfga` on every model push.
ARG TARGETARCH
ARG FGA_CLI_VERSION=0.7.19
ADD https://github.com/openfga/cli/releases/download/v${FGA_CLI_VERSION}/fga_${FGA_CLI_VERSION}_linux_${TARGETARCH}.tar.gz /tmp/fga.tar.gz
RUN tar -xzf /tmp/fga.tar.gz -C /usr/local/bin fga && rm /tmp/fga.tar.gz

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]