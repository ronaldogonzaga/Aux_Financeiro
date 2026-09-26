from pathlib import Path
from flask import Flask
from app.models import init_db

def create_app() -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'aux-financeiro-local-secret-key'
    app.config['DATABASE'] = Path(__file__).resolve().parent.parent / 'data' / 'aux_financeiro.db'
    app.config['TEMP_ZIPS'] = Path(__file__).resolve().parent.parent / 'temp_zips'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['DATABASE'].parent.mkdir(parents=True, exist_ok=True)
    app.config['TEMP_ZIPS'].mkdir(parents=True, exist_ok=True)
    init_db(app.config['DATABASE'])
    from app.routes import bp
    app.register_blueprint(bp)
    return app
