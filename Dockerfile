# Custom ERPNext image with loupe24k app bundled in
# Defaults to ERPNext v16; override with --build-arg FRAPPE_BRANCH=version-15 to target v15.
ARG FRAPPE_BRANCH=version-16
FROM frappe/erpnext:${FRAPPE_BRANCH}

USER root

# ERPNext v16 ships a MariaDB client (11.x) that defaults to requiring TLS.
# Our mariadb:10.6 dev db has no TLS configured, so `bench new-site` fails with
# "SSL is required, but the server does not support it". Disable the client's
# default TLS requirement for local dev; harmless no-op on v15 (older client
# default doesn't require TLS anyway).
RUN printf '[client]\nssl=0\n' > /etc/mysql/conf.d/no-ssl.cnf

# Copy the loupe24k app into the bench apps directory
COPY --chown=frappe:frappe apps/loupe24k /home/frappe/frappe-bench/apps/loupe24k

USER frappe

# Install the app as an editable package so Frappe can discover it
RUN /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir -e /home/frappe/frappe-bench/apps/loupe24k
