from flask import Blueprint

kuaishou_aoke_bp = Blueprint(
    'kuaishou_aoke',
    __name__,
    template_folder='../templates',
)

from . import routes
