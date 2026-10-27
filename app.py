import os
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, csrf, migrate
from routes import auth_bp, main_bp, interview_bp, api_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(api_bp)

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            "app_name": "AI Mock Interview",
            "prompt_version": Config.PROMPT_VERSION,
            "has_openai_key": bool(Config.OPENAI_API_KEY)
        }

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # Ensure tables are created
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
