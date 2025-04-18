# app/models.py
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login, bcrypt
from sqlalchemy import UniqueConstraint # Import UniqueConstraint

# New Model: LeaveType
class LeaveType(db.Model):
    __tablename__ = 'leave_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g., 'Annual', 'Casual', 'Instead Of'
    description = db.Column(db.Text, nullable=True)

    # Make it easy to query for display in forms
    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<LeaveType {self.name}>'

# New Model: EmployeeBalance
class EmployeeBalance(db.Model):
    __tablename__ = 'employee_balances'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    # Using Float for simplicity, consider Numeric(precision=10, scale=2) for production
    balance = db.Column(db.Float, nullable=False, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='balances')
    leave_type = db.relationship('LeaveType')

    # Ensure each user has only one balance record per leave type
    __table_args__ = (UniqueConstraint('user_id', 'leave_type_id', name='uq_user_leave_type'),)

    def __repr__(self):
        return f'<EmployeeBalance User: {self.user_id} Type: {self.leave_type_id} Balance: {self.balance}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='employee')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Leave Requests (one-to-many)
    leave_requests = db.relationship('LeaveRequest', backref='requester', lazy='dynamic', foreign_keys='LeaveRequest.user_id')
    reviewed_requests = db.relationship('LeaveRequest', backref='reviewer', lazy='dynamic', foreign_keys='LeaveRequest.reviewed_by')

    # Relationship to Balances (one-to-many)
    balances = db.relationship('EmployeeBalance', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # ... (rest of User model: set_password, check_password, __repr__, is_manager) ...
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

    @property
    def is_manager(self):
        return self.role == 'manager'

    # Helper to get balance for a specific leave type
    def get_balance(self, leave_type_id):
        balance_record = self.balances.filter_by(leave_type_id=leave_type_id).first()
        return balance_record.balance if balance_record else 0.0


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Add leave_type_id - Employee must select this when requesting
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    shift = db.Column(db.String(50), nullable=False) # e.g., 'Full Day', 'Morning'
    status = db.Column(db.String(20), nullable=False, default='Pending') # 'Pending', 'Approved', 'Disapproved'
    submitted_at = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    manager_comment = db.Column(db.Text, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship to LeaveType
    leave_type = db.relationship('LeaveType')

    def __repr__(self):
        type_name = self.leave_type.name if self.leave_type else 'Unknown Type'
        return f'<LeaveRequest {self.id} by User {self.user_id} for {self.request_date} ({type_name}) ({self.status})>'

    def can_review(self, user):
        return user.is_manager

    def can_cancel(self, user):
        return self.user_id == user.id and self.status == 'Pending'