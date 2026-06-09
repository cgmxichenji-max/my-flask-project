from flask import Blueprint

courier_fee_bp = Blueprint(
    'courier_fee',
    __name__,
    template_folder='../templates',
)

from . import routes  # noqa: E402, F401
