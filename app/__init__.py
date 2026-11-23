from flask import Flask
from .config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.services.history import initialize_database
    initialize_database(app.config["DATABASE_PATH"])

    from .routes import bp
    app.register_blueprint(bp)

    return app