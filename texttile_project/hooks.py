app_name = "texttile_project"
app_title = "TextTile Project"
app_publisher = "Meet Panara"
app_description = "This is for practice"
app_email = "panarammet78@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "texttile_project",
# 		"logo": "/assets/texttile_project/logo.png",
# 		"title": "TextTile Project",
# 		"route": "/texttile_project",
# 		"has_permission": "texttile_project.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/texttile_project/css/texttile_project.css"
# app_include_js = "/assets/texttile_project/js/texttile_project.js"

# include js, css files in header of web template
# web_include_css = "/assets/texttile_project/css/texttile_project.css"
# web_include_js = "/assets/texttile_project/js/texttile_project.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "texttile_project/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "texttile_project/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "texttile_project.utils.jinja_methods",
# 	"filters": "texttile_project.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "texttile_project.install.before_install"
# after_install = "texttile_project.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "texttile_project.uninstall.before_uninstall"
# after_uninstall = "texttile_project.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "texttile_project.utils.before_app_install"
# after_app_install = "texttile_project.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "texttile_project.utils.before_app_uninstall"
# after_app_uninstall = "texttile_project.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "texttile_project.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "texttile_project.notifications.get_notification_config"

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

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"texttile_project.tasks.all"
# 	],
# 	"daily": [
# 		"texttile_project.tasks.daily"
# 	],
# 	"hourly": [
# 		"texttile_project.tasks.hourly"
# 	],
# 	"weekly": [
# 		"texttile_project.tasks.weekly"
# 	],
# 	"monthly": [
# 		"texttile_project.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "texttile_project.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "texttile_project.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "texttile_project.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "texttile_project.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["texttile_project.utils.before_request"]
# after_request = ["texttile_project.utils.after_request"]

# Job Events
# ----------
# before_job = ["texttile_project.utils.before_job"]
# after_job = ["texttile_project.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"texttile_project.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			["dt", "in", ["Customer", "Sales Order"]]
		]
	},
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "in", ["Customer", "Sales Order"]]
		]
	},
	{
		"dt": "Client Script",
		"filters": [
			["dt", "in", ["Customer", "Sales Order"]]
		]
	},
	{
		"dt": "Custom DocPerm",
		"filters": [
			["parent", "in", ["Customer", "Sales Order"]]
		]
	}
]

