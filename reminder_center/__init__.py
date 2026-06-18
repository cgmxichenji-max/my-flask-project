from flask import Blueprint

reminder_center_bp = Blueprint(
    'reminder_center',
    __name__,
    template_folder='../templates',
)

from . import routes
