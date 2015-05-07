import os
import jinja2

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SESSION_COOKIE_NAME = 'dm_session'
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True
    DM_API_URL = None
    DM_API_AUTH_TOKEN = None
    DM_DATA_API_URL = None
    DM_DATA_API_AUTH_TOKEN = None
    DEBUG = False

    API_URL = os.getenv('DM_API_URL')
    API_AUTH_TOKEN = os.getenv('DM_SUPPLIER_FRONTEND_API_AUTH_TOKEN')

    MANDRILL_API_KEY = os.getenv('DM_MANDRILL_API_KEY')
    FORGOT_PASSWORD_EMAIL_NAME = 'Digital Marketplace Admin'
    FORGOT_PASSWORD_EMAIL_FROM = 'enquiries@digitalmarketplace.service.gov.uk'
    FORGOT_PASSWORD_EMAIL_SUBJECT = 'Reset your Digital Marketplace password'
    SECRET_KEY = os.getenv('DM_PASSWORD_SECRET_KEY')
    RESET_PASSWORD_SALT = 'ResetPasswordSalt'

    STATIC_URL_PATH = '/suppliers/static'
    ASSET_PATH = STATIC_URL_PATH + '/'
    BASE_TEMPLATE_DATA = {
        'asset_path': ASSET_PATH,
        'header_class': 'with-proposition'
    }

    # Logging
    DM_LOG_LEVEL = 'DEBUG'
    DM_APP_NAME = 'supplier-frontend'
    DM_LOG_PATH = '/var/log/digitalmarketplace/application.log'
    DM_DOWNSTREAM_REQUEST_ID_HEADER = 'X-Amz-Cf-Id'

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        template_folders = [
            os.path.join(repo_root,
                         'bower_components/govuk_template/views/layouts'),
            os.path.join(repo_root, 'app/templates')
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    DM_LOG_LEVEL = 'CRITICAL'
    DM_API_AUTH_TOKEN = 'test'
    DM_API_URL = 'http://localhost'
    DM_DATA_API_URL = os.getenv('DM_DATA_API_URL')
    DM_DATA_API_AUTH_TOKEN = os.getenv('DM_DATA_API_AUTH_TOKEN')
    WTF_CSRF_ENABLED = False


class Development(Config):
    DEBUG = True


class Live(Config):
    SESSION_COOKIE_DOMAIN = 'www.digitalmarketplace.service.gov.uk'
    DEBUG = False
    SESSION_COOKIE_SECURE = True


configs = {
    'development': Development,
    'preview': Live,
    'staging': Live,
    'production': Live,
    'test': Test,
}