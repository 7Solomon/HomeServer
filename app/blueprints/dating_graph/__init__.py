from flask import Blueprint

dating_graph_bp = Blueprint('dating_graph', __name__)

from app.blueprints.dating_graph import api