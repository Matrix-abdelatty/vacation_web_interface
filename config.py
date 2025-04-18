import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Load .env file



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # --- Start DB URI Logic ---
    DATABASE_URI_ENV = os.environ.get('DATABASE_URI')
    if DATABASE_URI_ENV and DATABASE_URI_ENV.startswith('sqlite:///'):
         # If it's the relative format 'sqlite:///filename.db' in .env
         db_filename = DATABASE_URI_ENV[len('sqlite:///'):]
         SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, db_filename)
         print(f"Constructed absolute SQLite URI: {SQLALCHEMY_DATABASE_URI}") # Debug print
    elif DATABASE_URI_ENV:
         # If .env specified a different type (postgres, mysql) or absolute sqlite path
         SQLALCHEMY_DATABASE_URI = DATABASE_URI_ENV
    else:
         # Default if nothing is in .env
         SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
         print(f"Using default SQLite URI: {SQLALCHEMY_DATABASE_URI}") # Debug print
    # --- End DB URI Logic ---

    SQLALCHEMY_TRACK_MODIFICATIONS = False















    # Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25) # Default port 25
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None and \
                   os.environ.get('MAIL_USE_TLS').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None and \
                   os.environ.get('MAIL_USE_SSL').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@example.com' # Set a default

    # Application specific config
    MANAGER_EMAIL = os.environ.get('MANAGER_EMAIL')
    # Define available shifts
    AVAILABLE_SHIFTS = ['Full Day', 'Morning', 'Evening', 'Night']