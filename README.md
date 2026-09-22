# Retail Platform

## Application

Retail Platform is a Flask-based application for enterprise DevOps deployment.
Git, Docker, Jenkins deployment, hotfix, and automated rollback workflows are demonstrated using this application.

## Production Versions

- v4.2.0 - Initial production release
- v4.2.1 - Payment defect hotfix
- v4.2.2 - Failure-injection version used to demonstrate automated rollback

## Git Branches

- `main` - Production-ready code
- `develop` - Ongoing development
- `release/4.3.0` - Release preparation
- `hotfix/payment-4.2.1` - Emergency payment fix

## Application Endpoints

- `/` - Application information
- `/health` - Health check
- `/version` - Application version
- `/payment` - Payment processing
- `/products` - Product information
- `/orders` - Order information

## Docker

Application port:

```text
8081