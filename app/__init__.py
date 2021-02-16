# app/__init__.py

# Third-party imports
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from app.mail.utils.mailtools import MailTool
from config import app_config

# SQLAlchemy variable initialization
db = SQLAlchemy()

# LoginManager variable initialization
login_manager = LoginManager()

app = None
mail = None


def create_app(config_name):
    # Models import
    from app import models

    # App configuration
    app = config_app(config_name)
    # Register blueprints
    config_blueprint(app)
    # Initialize db and login_manager
    init_db(app)

    # Initialize Bootstrap
    Bootstrap(app)
    # Initialize mails
    config_mail(app)

    return app


def config_app(config_name):
    """
    config app
    :return: app to be served
    """
    global app

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('config.py')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['BOOTSTRAP_SERVER_LOCAL'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app


def config_mail(app):
    """
    config mail settings
    :param app: app to be served
    """
    global mail
    mail_config = {
        'MAIL_SERVER': 'smtp.gmail.com',
        'MAIL_PORT': 465,
        'MAIL_USERNAME': 'noreply.agendaludique@gmail.com',
        'MAIL_DEFAULT_SENDER': 'Agenda Ludique',
        'MAIL_PASSWORD': 'uteokhqmpqwyjgdj',
        'MAIL_USE_TLS': False,
        'MAIL_USE_SSL': True
    }
    app.config.update(mail_config)
    mail = MailTool(app)


def config_blueprint(app):
    """
    add every blueprint that will be used
    :param app: app to be served
    """
    from app.site import site as site_blueprint  # renaming is totally useless
    from app.auth import auth as auth_blueprint
    from app.admin import admin_blueprint
    from app.games import bp_list
    from app.mail import mail as mail_blueprint
    from app.games.group import group as group_blueprint
    from app.games.session import session as session_blueprint

    app.register_blueprint(site_blueprint, url_prefix="/")
    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(mail_blueprint, url_prefix="/mail")
    app.register_blueprint(group_blueprint, url_prefix="/group")
    app.register_blueprint(session_blueprint, url_prefix="/session")
    for bp in bp_list:
        app.register_blueprint(bp)


def init_db(app):
    """
    init everything that is related to the db
    :param app: app to be served
    """
    global db

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_message = 'Vous devez être connecté pour avoir accès à cette page'
    login_manager.login_message_category = "warning"
    login_manager.login_view = 'auth.login'
    # Initialize Migrate
    migrate = Migrate(app, db)
