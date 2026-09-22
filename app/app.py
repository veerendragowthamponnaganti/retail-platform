from flask import Flask, jsonify
import os

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "4.2.0")
APP_ENV = os.getenv("APP_ENV", "development")
PAYMENT_MODE = os.getenv("PAYMENT_MODE", "normal")


@app.route("/")
def home():
    return jsonify({
        "application": "Retail Platform",
        "version": APP_VERSION,
        "environment": APP_ENV,
        "status": "running"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION
    }), 200


@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION
    })


@app.route("/payment")
def payment():
    # Version 4.2.0 contains a known payment defect.
    # This defect will be fixed in hotfix version 4.2.1.
    return jsonify({
        "payment_status": "FAILED",
        "message": "Payment failed due to known payment processing defect",
        "version": APP_VERSION
    }), 500


@app.route("/products")
def products():
    return jsonify({
        "products": [
            {
                "id": 1,
                "name": "Laptop",
                "price": 55000
            },
            {
                "id": 2,
                "name": "Smartphone",
                "price": 25000
            }
        ],
        "version": APP_VERSION
    })


@app.route("/orders")
def orders():
    return jsonify({
        "orders": [
            {
                "order_id": 1001,
                "product": "Laptop",
                "quantity": 1,
                "status": "CONFIRMED"
            },
            {
                "order_id": 1002,
                "product": "Smartphone",
                "quantity": 2,
                "status": "PROCESSING"
            }
        ],
        "version": APP_VERSION
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8081
    )