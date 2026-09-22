# Retail Platform

## Application

Retail Platform is a Flask-based application used to demonstrate an enterprise
Git, Docker, Jenkins deployment, hotfix, and automated rollback workflow.

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