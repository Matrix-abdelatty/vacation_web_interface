from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Failed to send email: {e}", exc_info=True) # Log errors

def send_email(subject, recipients, text_body, html_body):
    app = current_app._get_current_object() # Get the actual app instance
    if not app.config['MAIL_SERVER']:
        app.logger.warning("Mail server not configured. Email not sent.")
        return # Don't try to send if mail isn't configured
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Send email in a background thread
    thread = Thread(target=send_async_email, args=[app, msg])
    thread.start()
    return thread # Optional: return thread if you need to join later

def send_new_request_notification(user, leave_request):
    manager_email = current_app.config.get('MANAGER_EMAIL')
    if not manager_email:
        current_app.logger.warning("MANAGER_EMAIL not set. Cannot send notification.")
        return

    subject = f"New Leave Request from {user.username}"
    send_email(
        subject,
        recipients=[manager_email],
        text_body=render_template('email/new_request.txt',
                                  user=user, request=leave_request),
        html_body=render_template('email/new_request.html',
                                  user=user, request=leave_request)
    )