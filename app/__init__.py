import os
import yaml
import logging
import logging.config
from logging import getLogger
from pathlib import Path
import sqlite3
from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from dynaconf import FlaskDynaconf

login_manager = LoginManager()
login_manager.login_view = "auth_bp.login"
flask_bcrypt = Bcrypt()
db = SQLAlchemy()
migrate = Migrate()

def create_app():  
    app = Flask(__name__)
    dynaconf = FlaskDynaconf(extensions_list= True)
    with app.app_context():

        logger = getLogger(__file__)

        @app.route('/')
        def index():
            app.logger.debug("rendering index page")
        # to do the dashboard of total orders and price, plus amount spent by customers, we need to 
        # loop through all orders to get customer_id, which we can look up, and for each order retrieve all line items,
        # and then loop through all line items to retrieve product_id and then look up
        # product price and then total this with quantity
        # as we find the value we want from each item, we can put that into a list, or maybe dictionary, to use in the dashboard
            return render_template('index.html')
        
        # initialize plugins
        os.environ["ROOT_PATH_FOR_DYNACONF"] = app.root_path
        dynaconf.init_app(app)

        # turn the secret key into a bytearray
        app.config["SECRET_KEY"] = bytearray(app.config["SECRET_KEY"], "UTF-8")
        _configure_logging(app, dynaconf)

        # load the configuration to smooth database connections
        app.config.from_object(__name__)

        # database details - to remove some duplication
        db_name = 'shopping_data.db'

        # code based on example at https://github.com/mjhea0/flaskr-tdd

        def connect_db():
            conn = sqlite3.connect(db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            conn.row_factory = sqlite3.Row
            return conn

        def get_db():
            if not hasattr(g, 'sqlite_db'):
                g.sqlite_db = connect_db()
            return g.sqlite_db

        def close_db(error):
            if hasattr(g, 'sqlite_db'):
                g.sqlite_db.close()

        @app.route('/customers')
        def customers():
            db = get_db()
            # get results from customers
            cur = db.execute("select * from customers")
            rows = cur.fetchall()
            app.logger.debug("rendering customer page")
            return render_template('customers.html', rows=rows)

        @app.route('/customer_details/<id>')
        def customer_details(id):
            db = get_db()
            # get results from customers
            cur = db.execute("select * from customers WHERE id=?", (id))
            customer = cur.fetchall()
            cur = db.execute("select * from orders WHERE customer_id=?", (id))
            # we call this 'rows' instead of 'orders' as the later causes confusion in 
            # call to order_details page, which has object called 'orders' too
            rows = cur.fetchall()
            return render_template('customer_details.html', customer=customer, rows=rows)

        @app.route('/orders')
        def orders():
            db = get_db()
            # get results from orders
            cur = db.execute("select * from orders")
            rows = cur.fetchall()
            app.logger.debug("rendering orders page")
            return render_template('orders.html', rows=rows)

        @app.route('/order_details/<id>')
        def order_details(id):
            db = get_db()
            # get results from orders
            cur = db.execute("select * from orders WHERE id=?", (id))
            order = cur.fetchall()
            customer_id = order[0]['customer_id']
            cur = db.execute("select * from customers WHERE id=?", (customer_id,))
            customer = cur.fetchall()
            cur = db.execute("select * from line_items WHERE order_id=?", (id))
            items = cur.fetchall()
            return render_template('order_details.html', order=order, items=items, customer=customer)

        @app.route('/products')
        def products():
            db = get_db()
            # get results from products
            cur = db.execute("select * from products")
            rows = cur.fetchall()
            app.logger.debug("rendering products page")
            return render_template('products.html', rows=rows)
        
        return app


def _configure_logging(app, dynaconf):
    # configure logging
    logging_config_path = Path(app.root_path).parent / "logging_config.yaml"
    with open(logging_config_path, "r") as fh:
        logging_config = yaml.safe_load(fh.read())
        env_logging_level = dynaconf.settings.get("logging_level", "INFO").upper()
        logging_level = logging.INFO if env_logging_level == "INFO" else logging.DEBUG
        logging_config["handlers"]["console"]["level"] = logging_level
        logging_config["loggers"][""]["level"] = logging_level
        logging.config.dictConfig(logging_config)
