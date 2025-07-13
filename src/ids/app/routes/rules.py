from flask import Blueprint, render_template
from flask_login import login_required

rules_bp = Blueprint('rules', __name__)

@rules_bp.route('/rules')
@login_required
def rules():
    """规则管理页面"""
    return render_template('rules.html') 