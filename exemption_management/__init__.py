from flask import Blueprint

exemption_management_bp = Blueprint(
    'exemption_management',
    __name__,
    template_folder='../templates',
)

from . import routes
