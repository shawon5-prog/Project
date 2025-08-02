from .auth import auth_bp
from .dashboard import dashboard_bp
from .mbbs_result import mbbs_result_bp
from .bds_result import bds_result_bp
from .mbbs_pass_recover import mbbs_pass_recover_bp
from .bds_pass_recover import bds_pass_recover_bp
from .mbbs_user_id import mbbs_user_id_bp
from .bds_user_id import bds_user_id_bp
from .management import management_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(mbbs_result_bp)
    app.register_blueprint(bds_result_bp)
    app.register_blueprint(mbbs_pass_recover_bp)
    app.register_blueprint(bds_pass_recover_bp)
    app.register_blueprint(mbbs_user_id_bp)
    app.register_blueprint(bds_user_id_bp)
    app.register_blueprint(management_bp)

