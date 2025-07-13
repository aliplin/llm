from flask import Blueprint, render_template
from flask_login import login_required

events_bp = Blueprint('events', __name__)

@events_bp.route('/events')
@login_required
def events():
    """事件日志页面"""
    return render_template('events.html') 