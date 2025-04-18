import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from config import Config
import logging


from datetime import datetime 







db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
# Update login_view to include the Blueprint name ('main') followed by the function name
login.login_view = 'main.login'
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info'
mail = Mail()
bcrypt = Bcrypt()

# Import models after db is defined
# This should be okay here as models.py only needs the db object definition
from app import models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True # Also set it directly on the environment
    print(f"Templates Auto Reload: {app.config['TEMPLATES_AUTO_RELOAD']}") # Verify





    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)

    # Import the Blueprint *after* app is created
    from app.routes import bp as main_blueprint # Import the 'bp' variable
    # Register the Blueprint with the app
    app.register_blueprint(main_blueprint)


    @app.context_processor
    def inject_now():
        # Makes 'now' available in all templates
        return {'now': datetime.utcnow()}
        # Use datetime.now() if you prefer server's local time zone

        

    # Configure logging
    if not app.debug and not app.testing:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('LeaveFlow startup')

    # Error Handlers (remain inside create_app)
    @app.errorhandler(404)
    def not_found_error(error):
         return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error('Server Error: %s', (error), exc_info=True)
        try:
            db.session.rollback()
        except Exception as e:
            app.logger.error('Error during DB rollback: %s', e)
        return render_template('500.html'), 500

    app.logger.info("LeaveFlow application created and blueprint registered.")

    return app

# Note: The 'from app import models' below the function is no longer strictly necessary
# if it's already imported above, but doesn't hurt.
# from app import models