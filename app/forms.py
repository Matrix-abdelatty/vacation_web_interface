# app/forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     SelectField, DateField, TextAreaField, FloatField) # Add FloatField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField # Import QuerySelectField
from app.models import User, LeaveType, EmployeeBalance # Import new models
from datetime import date
from flask import current_app
from flask_login import current_user

# --- Existing Forms (LoginForm, RegistrationForm, EmptyForm) ---
# No changes needed for LoginForm, RegistrationForm, EmptyForm

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('employee', 'Employee'), ('manager', 'Manager')],
                       validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class EmptyForm(FlaskForm):
    pass

# --- Leave Request Form Modification ---

# Helper function to query available leave types
def get_leave_types():
    return LeaveType.query.order_by(LeaveType.name).all()

class LeaveRequestForm(FlaskForm):
    # Add QuerySelectField for Leave Type
    leave_type = QuerySelectField('Leave Type', query_factory=get_leave_types,
                                  get_label='name', allow_blank=False, validators=[DataRequired()])
    request_date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    shift = SelectField('Shift', choices=[], validators=[DataRequired()])
    submit = SubmitField('Submit Request')

    def __init__(self, *args, **kwargs):
        super(LeaveRequestForm, self).__init__(*args, **kwargs)
        self.shift.choices = [(shift, shift) for shift in current_app.config['AVAILABLE_SHIFTS']]

    def validate_request_date(self, request_date):
        if request_date.data <= date.today():
            raise ValidationError('Leave date must be in the future.')

    # New Validation: Check if employee has enough balance for the selected leave type
    def validate_leave_type(self, leave_type):
        if not current_user.is_authenticated: # Should not happen due to @login_required
             raise ValidationError("Authentication error.")
        leave_type_obj = leave_type.data # The selected LeaveType object
        if leave_type_obj:
            current_balance = current_user.get_balance(leave_type_obj.id)
            # Assuming 1 request = 1 day/unit. Adapt if requests can be for >1 day.
            if current_balance < 1.0:
                raise ValidationError(f"Insufficient '{leave_type_obj.name}' balance ({current_balance:.1f} remaining).")

# --- Manager Forms ---

# Form for Manager to Set/Update Balances
def get_employees():
    return User.query.filter_by(role='employee').order_by(User.username).all()

class ManagerSetBalanceForm(FlaskForm):
    employee = QuerySelectField('Employee', query_factory=get_employees, get_label='username',
                                allow_blank=False, validators=[DataRequired()])
    leave_type = QuerySelectField('Leave Type', query_factory=get_leave_types, get_label='name',
                                  allow_blank=False, validators=[DataRequired()])
    new_balance = FloatField('New Balance', validators=[DataRequired(), NumberRange(min=0)], default=0.0)
    submit = SubmitField('Set/Update Balance')


# No changes needed for ManagerActionForm
class ManagerActionForm(FlaskForm):
    comment = TextAreaField('Reason for Disapproval (Optional)', validators=[Optional(), Length(max=500)])
    submit_approve = SubmitField('Approve Request')
    submit_disapprove = SubmitField('Disapprove Request')