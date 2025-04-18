from flask import (render_template, flash, redirect, url_for, request,
                   current_app, abort, Blueprint)
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlsplit
from datetime import datetime
from flask_wtf.csrf import generate_csrf

from app import db
# Import new models and forms
from app.models import User, LeaveRequest, LeaveType, EmployeeBalance
from app.forms import (LoginForm, RegistrationForm, LeaveRequestForm,
                       ManagerActionForm, ManagerSetBalanceForm) 
from app.email import send_new_request_notification
from app.decorators import manager_required, employee_required

    

# Create a Blueprint instance
# The first argument 'main' is the blueprint's name, used in url_for (e.g., 'main.login')
# The second argument __name__ helps Flask locate templates/static files if needed
bp = Blueprint('main', __name__)

# === Core Routes ===
# Use @bp.route instead of @current_app.route

# NOTE: We define landing_page and login under the blueprint now.
# Make sure url_for calls reflect this (e.g., url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_manager:
             return redirect(url_for('main.manager_dashboard')) # Use blueprint name
        else:
             return redirect(url_for('main.employee_dashboard')) # Use blueprint name

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login')) # Use blueprint name
        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back, {user.username}!', 'success')

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc:
            if user.is_manager:
                next_page = url_for('main.manager_dashboard') # Use blueprint name
            else:
                next_page = url_for('main.employee_dashboard') # Use blueprint name
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/')
@bp.route('/index')
def landing_page():
    if current_user.is_authenticated:
         if current_user.is_manager:
             return redirect(url_for('main.manager_dashboard')) # Use blueprint name
         else:
             return redirect(url_for('main.employee_dashboard')) # Use blueprint name
    # If not authenticated, redirect to the blueprint's login view
    return redirect(url_for('main.login')) # Use blueprint name

@bp.route('/logout')
@login_required # Still good practice to require login for logout action
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login')) # Redirect to login page

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        # Redirect logged-in users away from registration
        if current_user.is_manager:
            return redirect(url_for('main.manager_dashboard'))
        else:
            return redirect(url_for('main.employee_dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} registered successfully! Please log in.', 'success')
        return redirect(url_for('main.login')) # Redirect to login after registration
    return render_template('register.html', title='Register', form=form)







# --- Employee Routes ---

@bp.route('/dashboard')
@login_required
@employee_required
def employee_dashboard():
    requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.submitted_at.desc()).all()
    # Fetch balances to display
    balances = EmployeeBalance.query.filter_by(user_id=current_user.id).join(LeaveType).order_by(LeaveType.name).all()
    return render_template('employee/dashboard.html', title='My Requests', requests=requests, balances=balances)

@bp.route('/request_leave', methods=['GET', 'POST'])
@login_required
@employee_required
def request_leave():
    form = LeaveRequestForm()
    # Form validation now includes the balance check (validate_leave_type)
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            user_id=current_user.id,
            leave_type_id=form.leave_type.data.id, # Get ID from selected object
            request_date=form.request_date.data,
            shift=form.shift.data,
            status='Pending'
        )
        db.session.add(leave_request)
        # Don't deduct balance here, only upon approval
        db.session.commit()
        flash('Leave request submitted successfully!', 'success')
        try:
            send_new_request_notification(current_user, leave_request)
            current_app.logger.info(f"Notification email sent for request {leave_request.id}")
        except Exception as e:
            current_app.logger.error(f"Failed to send notification email for request {leave_request.id}: {e}")
        return redirect(url_for('main.employee_dashboard'))
    else:
        # Flash form errors if any (including insufficient balance)
        for field, errors in form.errors.items():
            for error in errors:
                 # Avoid flashing the default CSRF error message if it's the only one
                if field != 'csrf_token':
                    flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')

    return render_template('employee/request_form.html', title='Request Leave', form=form)





# --- Manager Routes ---

@bp.route('/manager/dashboard')
@login_required
@manager_required
def manager_dashboard():
    csrf_token_value = generate_csrf()
    status_filter = request.args.get('status', 'Pending')
    query = LeaveRequest.query.order_by(LeaveRequest.submitted_at.desc())
    if status_filter == 'Pending':
        query = query.filter_by(status='Pending')
    elif status_filter == 'Approved':
         query = query.filter_by(status='Approved')
    elif status_filter == 'Disapproved':
         query = query.filter_by(status='Disapproved')
    else:
        status_filter = 'All'
    requests = query.all()
    return render_template(
        'manager/dashboard.html', title='Manager Dashboard',
        requests=requests, current_filter=status_filter,
        csrf_token=csrf_token_value
    )

@bp.route('/manager/approve/<int:request_id>', methods=['POST'])
@login_required
@manager_required
def approve_request(request_id):
    leave_request = db.session.get(LeaveRequest, request_id)
    if leave_request is None:
        flash('Request not found.', 'danger')
        abort(404)
    if leave_request.status != 'Pending':
        flash('Request already processed.', 'warning')
        return redirect(url_for('main.manager_dashboard'))

    # --- Balance Deduction Logic ---
    employee = leave_request.requester
    balance_record = EmployeeBalance.query.filter_by(
        user_id=employee.id,
        leave_type_id=leave_request.leave_type_id
    ).first()

    # Assume 1 request = 1 day/unit. Needs adjustment for multi-day requests.
    leave_cost = 1.0

    if balance_record is None or balance_record.balance < leave_cost:
        flash(f'Cannot approve: Insufficient {leave_request.leave_type.name} balance for {employee.username}.', 'danger')
        return redirect(url_for('main.manager_dashboard'))

    # Deduct balance
    balance_record.balance -= leave_cost
    balance_record.last_updated = datetime.utcnow()
    db.session.add(balance_record) # Add record to session for update

    # --- Update Request Status ---
    leave_request.status = 'Approved'
    leave_request.reviewed_by = current_user.id
    leave_request.reviewed_at = datetime.utcnow()
    # Optionally add comment if needed for approval too
    # leave_request.manager_comment = request.form.get('comment')

    try:
        db.session.commit() # Commit both balance update and request status
        flash(f'Request from {leave_request.requester.username} for {leave_request.request_date.strftime("%Y-%m-%d")} approved. Balance updated.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving request {request_id}: {e}")
        flash('An error occurred while approving the request. Please try again.', 'danger')

    # Optional: Send notification email to employee
    return redirect(url_for('main.manager_dashboard'))

@bp.route('/manager/disapprove/<int:request_id>', methods=['POST'])
@login_required
@manager_required
def disapprove_request(request_id):
    # No changes needed here as disapproval doesn't affect balance
    leave_request = db.session.get(LeaveRequest, request_id)
    if leave_request is None:
        flash('Request not found.', 'danger')
        abort(404)
    if leave_request.status != 'Pending':
        flash('Request already processed.', 'warning')
        return redirect(url_for('main.manager_dashboard'))

    comment = request.form.get('comment', None)
    leave_request.status = 'Disapproved'
    leave_request.reviewed_by = current_user.id
    leave_request.reviewed_at = datetime.utcnow()
    leave_request.manager_comment = comment
    db.session.commit()
    flash(f'Request from {leave_request.requester.username} for {leave_request.request_date.strftime("%Y-%m-%d")} disapproved.', 'success')
    return redirect(url_for('main.manager_dashboard'))


# --- New Manager Routes for Balances and Reporting ---

@bp.route('/manager/balances', methods=['GET', 'POST'])
@login_required
@manager_required
def manage_balances():
    form = ManagerSetBalanceForm()
    if form.validate_on_submit():
        employee = form.employee.data
        leave_type = form.leave_type.data
        new_balance_value = form.new_balance.data

        # Find existing balance or create a new one
        balance_record = EmployeeBalance.query.filter_by(
            user_id=employee.id,
            leave_type_id=leave_type.id
        ).first()

        if balance_record:
            balance_record.balance = new_balance_value
            balance_record.last_updated = datetime.utcnow()
            flash(f"Updated {employee.username}'s {leave_type.name} balance to {new_balance_value}.", 'success')
        else:
            balance_record = EmployeeBalance(
                user_id=employee.id,
                leave_type_id=leave_type.id,
                balance=new_balance_value
            )
            db.session.add(balance_record)
            flash(f"Set {employee.username}'s {leave_type.name} balance to {new_balance_value}.", 'success')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating balance: {e}")
            flash('An error occurred while updating the balance.', 'danger')

        return redirect(url_for('main.manage_balances')) # Redirect to refresh view

    # GET request: Display current balances
    employees = User.query.filter_by(role='employee').order_by(User.username).all()
    # Eager load balances and leave types for efficiency
    all_balances = db.session.query(EmployeeBalance).options(
            db.joinedload(EmployeeBalance.user),
            db.joinedload(EmployeeBalance.leave_type)
        ).order_by(EmployeeBalance.user_id, EmployeeBalance.leave_type_id).all()

    # Organize balances by employee for easier display in template
    balances_by_employee = {}
    for emp in employees:
        balances_by_employee[emp.id] = {'user': emp, 'balances': []}
    for bal in all_balances:
        if bal.user_id in balances_by_employee:
             balances_by_employee[bal.user_id]['balances'].append(bal)


    csrf_token_val = generate_csrf() # For any potential forms on the page
    return render_template('manager/manage_balances.html',
                           title="Manage Balances", form=form,
                           balances_data=balances_by_employee,
                           csrf_token=csrf_token_val)


@bp.route('/manager/leave_report')
@login_required
@manager_required
def leave_report():
    # Simple report: Get all approved requests
    approved_requests = LeaveRequest.query.filter_by(status='Approved') \
        .join(User, LeaveRequest.user_id == User.id) \
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id) \
        .options(db.contains_eager(LeaveRequest.requester), db.contains_eager(LeaveRequest.leave_type)) \
        .order_by(User.username, LeaveRequest.request_date.desc()).all()

    # Fetch current balances for summary (similar to manage_balances GET)
    employees = User.query.filter_by(role='employee').order_by(User.username).all()
    balances_by_employee = {}
    leave_types = LeaveType.query.order_by(LeaveType.name).all() # Get all types for headers
    for emp in employees:
        balances_by_employee[emp.id] = {'user': emp, 'balances': {}}
        for lt in leave_types:
             balances_by_employee[emp.id]['balances'][lt.name] = emp.get_balance(lt.id)


    return render_template('manager/leave_report.html',
                           title="Leave Report",
                           requests=approved_requests,
                           balances_data=balances_by_employee,
                           leave_types=leave_types)