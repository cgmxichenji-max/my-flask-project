from flask import Blueprint

kuaishou_meizhuang_bp = Blueprint(
    'kuaishou_meizhuang',
    __name__,
    template_folder='../templates',
)

from . import routes
