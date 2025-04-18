from app import create_app, db
from app.models import User, LeaveRequest # Import models

# Create the Flask app instance using the factory function
app = create_app()

# Make db, User, LeaveRequest available in 'flask shell' context
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'LeaveRequest': LeaveRequest}

if __name__ == '__main__':
    # Use app.run() only for development.
    # For production, use a WSGI server like Gunicorn or uWSGI.
    # Debug mode should be False in production.
    # host='0.0.0.0' makes it accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('FLASK_DEBUG', True))