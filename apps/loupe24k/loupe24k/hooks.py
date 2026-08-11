app_name = "loupe24k"
app_title = "Loupe 24K"
app_publisher = "Fafadia Tech"
app_description = "ERPNext Customization for Jewellery Business"
app_email = "sidharth@fafadiatech.com"
app_license = "MIT"

# Required Apps
# required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/loupe24k/css/loupe24k.css"
# app_include_js = "/assets/loupe24k/js/loupe24k.js"

# include js, css files in header of web template
# web_include_css = "/assets/loupe24k/css/loupe24k.css"
# web_include_js = "/assets/loupe24k/js/loupe24k.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "loupe24k.install.before_install"
after_install = "loupe24k.setup.install.after_install"
after_migrate = "loupe24k.setup.install.after_migrate"

# Desk Notifications
# ------------------

# See frappe.core.notifications.get_notification_config
# notification_config = "loupe24k.notifications.get_notification_config"

# Permissions
# -----------

# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    "Job Card": {
        "on_submit": "loupe24k.loupe_24k.doctype.job_card_sync.on_submit",
        "on_update_after_submit": "loupe24k.loupe_24k.doctype.job_card_sync.on_update_after_submit",
        "on_cancel": "loupe24k.loupe_24k.doctype.job_card_sync.on_cancel",
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"loupe24k.tasks.all"
# 	],
# 	"daily": [
# 		"loupe24k.tasks.daily"
# 	],
# 	"hourly": [
# 		"loupe24k.tasks.hourly"
# 	],
# 	"weekly": [
# 		"loupe24k.tasks.weekly"
# 	],
# 	"monthly": [
# 		"loupe24k.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "loupe24k.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "loupe24k.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "loupe24k.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]
