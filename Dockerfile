# Custom ERPNext v15 image with loupe24k app bundled in
FROM frappe/erpnext:version-15

USER root

# Copy the loupe24k app into the bench apps directory
COPY --chown=frappe:frappe apps/loupe24k /home/frappe/frappe-bench/apps/loupe24k

USER frappe

# Install the app as an editable package so Frappe can discover it
RUN /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir -e /home/frappe/frappe-bench/apps/loupe24k
