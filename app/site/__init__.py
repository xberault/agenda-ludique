# app/site/__init__.py

from flask import Blueprint

site = Blueprint('site', __name__, template_folder="templates", static_folder="static", static_url_path="/site/static")

from app.site import views
