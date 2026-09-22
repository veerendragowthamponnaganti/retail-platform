```groovy
pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOYMENT_ACTION',
            choices: ['DEPLOY', 'ROLLBACK'],
            description: 'Choose deployment action'
        )

        choice(
            name: 'ENVIRONMENT',
            choices: ['UAT', 'PRODUCTION'],
            description: 'Choose deployment environment'
        )

        string(
            name: 'VERSION',
            defaultValue: 'v4.2.1',
            description: 'Git tag/version to deploy'
        )

        choice(
            name: 'CONFIRM_PROD',
            choices: ['NO', 'YES'],
            description: 'Production deployment confirmation'
        )
    }

    environment {
        DOCKER = 'C:\\Users\\ASUS\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe'
        IMAGE_REPOSITORY = 'retail-app'
        NETWORK_NAME = 'retail-network'
    }

    stages {

        stage('Show Parameters') {
            steps {
                echo "=========================================="
                echo "DEPLOYMENT ACTION : ${params.DEPLOYMENT_ACTION}"
                echo "ENVIRONMENT       : ${params.ENVIRONMENT}"
                echo "REQUESTED VERSION : ${params.VERSION}"
                echo "PRODUCTION CONFIRM: ${params.CONFIRM_PROD}"
                echo "=========================================="
            }
        }

        stage('Validate Parameters') {
            steps {
                script {
                    if (params.ENVIRONMENT == 'PRODUCTION' &&
                        params.CONFIRM_PROD != 'YES') {

                        error(
                            "Production deployment blocked. CONFIRM_PROD must be YES."
                        )
                    }

                    if (params.DEPLOYMENT_ACTION == 'ROLLBACK' &&
                        params.ENVIRONMENT != 'PRODUCTION') {

                        error(
                            "ROLLBACK is allowed only for PRODUCTION."
                        )
                    }

                    echo "Parameter validation successful."
                }
            }
        }

        stage('Checkout Requested Version') {
            steps {
                script {
                    bat """
                        @echo off

                        git fetch --tags --force

                        git rev-parse --verify refs/tags/${params.VERSION}

                        git checkout --force tags/${params.VERSION}

                        echo.
                        echo ===== SELECTED GIT COMMIT =====
                        git rev-parse HEAD

                        echo.
                        echo ===== SELECTED VERSION =====
                        git describe --tags --exact-match HEAD
                    """
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    env.BUILD_IMAGE =
                        "${env.IMAGE_REPOSITORY}:${params.VERSION}-${env.BUILD_NUMBER}"

                    echo "Building Docker image:"
                    echo "${env.BUILD_IMAGE}"

                    bat """
                        @echo off

                        "%DOCKER%" build ^
                            -t "${env.BUILD_IMAGE}" .

                        echo.
                        echo ===== DOCKER IMAGE CREATED =====

                        "%DOCKER%" images "${env.IMAGE_REPOSITORY}"
                    """
                }
            }
        }

        stage('Create Docker Network') {
            steps {
                bat """
                    @echo off

                    "%DOCKER%" network inspect "${env.NETWORK_NAME}" >nul 2>&1

                    if errorlevel 1 (
                        echo Creating Docker network...
                        "%DOCKER%" network create "${env.NETWORK_NAME}"
                    ) else (
                        echo Docker network already exists.
                    )
                """
            }
        }

        stage('Record Previous Production') {
            when {
                expression {
                    params.ENVIRONMENT == 'PRODUCTION'
                }
            }

            steps {
                script {

                    def inspectStatus = bat(
                        returnStatus: true,
                        script: '''
                            @echo off

                            "%DOCKER%" inspect ^
                                --format="{{.Config.Image}}" ^
                                retail-app-production ^
                                > previous-image.txt 2>nul
                        '''
                    )

                    def previousImage = 'NONE'

                    if (inspectStatus == 0) {

                        previousImage =
                            readFile('previous-image.txt').trim()

                        if (!previousImage) {
                            previousImage = 'NONE'
                        }
                    }

                    env.PREVIOUS_PRODUCTION_IMAGE = previousImage

                    echo "Previous production image: ${env.PREVIOUS_PRODUCTION_IMAGE}"
                }
            }
        }

        stage('Rollback Action') {
            when {
                allOf {
                    expression {
                        params.DEPLOYMENT_ACTION == 'ROLLBACK'
                    }

                    expression {
                        params.ENVIRONMENT == 'PRODUCTION'
                    }
                }
            }

            steps {
                script {

                    echo "=========================================="
                    echo "MANUAL ROLLBACK REQUESTED"
                    echo "=========================================="

                    def rollbackImage =
                        env.PREVIOUS_PRODUCTION_IMAGE

                    if (!rollbackImage ||
                        rollbackImage == 'NONE') {

                        rollbackImage = "${env.IMAGE_REPOSITORY}:v4.2.1"
                    }

                    echo "Rollback image: ${rollbackImage}"

                    bat """
                        @echo off

                        "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0

                        "%DOCKER%" run -d ^
                            --name retail-app-production ^
                            --network "${env.NETWORK_NAME}" ^
                            -p 8081:8081 ^
                            -e APP_VERSION=4.2.1 ^
                            -e APP_ENV=production ^
                            -e PAYMENT_MODE=normal ^
                            --cpus="1.0" ^
                            --memory="512m" ^
                            -v retail-data:/app/data ^
                            "${rollbackImage}"
                    """

                    echo "Manual rollback container started."
                }
            }
        }

        stage('Deploy') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    /*
                     * Production candidate uses 8083 so that
                     * production v4.2.1 can remain running on 8081
                     * while the new version is validated.
                     *
                     * UAT candidate uses 8082.
                     */
                    def candidatePort =
                        params.ENVIRONMENT == 'PRODUCTION'
                            ? '8083'
                            : '8082'

                    def finalPort =
                        params.ENVIRONMENT == 'PRODUCTION'
                            ? '8081'
                            : '8082'

                    def candidateName =
                        "retail-app-candidate-${env.BUILD_NUMBER}"

                    def finalName =
                        params.ENVIRONMENT == 'PRODUCTION'
                            ? 'retail-app-production'
                            : 'retail-app-uat'

                    env.CANDIDATE_NAME = candidateName
                    env.FINAL_NAME = finalName
                    env.CANDIDATE_PORT = candidatePort
                    env.DEPLOY_PORT = finalPort

                    echo "=========================================="
                    echo "DEPLOYMENT START"
                    echo "Environment    : ${params.ENVIRONMENT}"
                    echo "Version        : ${params.VERSION}"
                    echo "Image          : ${env.BUILD_IMAGE}"
                    echo "Candidate      : ${candidateName}"
                    echo "Candidate Port : ${candidatePort}"
                    echo "Final          : ${finalName}"
                    echo "Final Port     : ${finalPort}"
                    echo "=========================================="

                    try {

                        /*
                         * Start new version first.
                         *
                         * PRODUCTION:
                         * candidate -> host 8083 -> container 8081
                         *
                         * UAT:
                         * candidate -> host 8082 -> container 8081
                         */
                        bat """
                            @echo off

                            "%DOCKER%" rm -f "${candidateName}" >nul 2>&1 || exit /b 0

                            "%DOCKER%" run -d ^
                                --name "${candidateName}" ^
                                --network "${env.NETWORK_NAME}" ^
                                -p ${candidatePort}:8081 ^
                                -e APP_VERSION=${params.VERSION} ^
                                -e APP_ENV=${params.ENVIRONMENT.toLowerCase()} ^
                                -e PAYMENT_MODE=normal ^
                                --cpus="1.0" ^
                                --memory="512m" ^
                                -v retail-data:/app/data ^
                                "${env.BUILD_IMAGE}"
                        """

                        echo "Candidate container started."

                        /*
                         * Wait for Docker health check.
                         */
                        script {

                            def healthy = false

                            for (int i = 1; i <= 12; i++) {

                                sleep 5

                                def healthStatus = bat(
                                    returnStdout: true,
                                    script: """
                                        @echo off

                                        "%DOCKER%" inspect ^
                                            --format="{{.State.Health.Status}}" ^
                                            "${candidateName}"
                                    """
                                ).trim()

                                echo "Health check ${i}/12: ${healthStatus}"

                                if (healthStatus == 'healthy') {
                                    healthy = true
                                    break
                                }

                                if (healthStatus == 'unhealthy') {
                                    break
                                }
                            }

                            if (!healthy) {

                                echo "Candidate health check FAILED."

                                error(
                                    "Health check failed for ${candidateName}"
                                )
                            }
                        }

                        echo "Candidate health check PASSED."

                        /*
                         * UAT:
                         * Remove candidate before final container
                         * because both use port 8082.
                         */
                        if (params.ENVIRONMENT == 'UAT') {

                            bat """
                                @echo off

                                "%DOCKER%" rm -f "${candidateName}"
                            """

                            echo "UAT candidate removed after successful health check."

                            bat """
                                @echo off

                                "%DOCKER%" rm -f "${finalName}" >nul 2>&1 || exit /b 0

                                "%DOCKER%" run -d ^
                                    --name "${finalName}" ^
                                    --network "${env.NETWORK_NAME}" ^
                                    -p ${finalPort}:8081 ^
                                    -e APP_VERSION=${params.VERSION} ^
                                    -e APP_ENV=uat ^
                                    -e PAYMENT_MODE=normal ^
                                    --cpus="1.0" ^
                                    --memory="512m" ^
                                    -v retail-data:/app/data ^
                                    "${env.BUILD_IMAGE}"
                            """

                            echo "UAT deployment started."

                        } else {

                            /*
                             * PRODUCTION:
                             *
                             * Old production remains on 8081
                             * while candidate is validated on 8083.
                             *
                             * Only after candidate becomes healthy
                             * do we remove old production.
                             */
                            echo "Production candidate is healthy."
                            echo "Candidate was validated on port 8083."
                            echo "Removing old production container..."

                            bat """
                                @echo off

                                "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0
                            """

                            /*
                             * Candidate has already been validated.
                             * Recreate production on port 8081.
                             */
                            bat """
                                @echo off

                                "%DOCKER%" rm -f "${candidateName}" >nul 2>&1 || exit /b 0

                                "%DOCKER%" run -d ^
                                    --name retail-app-production ^
                                    --network "${env.NETWORK_NAME}" ^
                                    -p 8081:8081 ^
                                    -e APP_VERSION=${params.VERSION} ^
                                    -e APP_ENV=production ^
                                    -e PAYMENT_MODE=normal ^
                                    --cpus="1.0" ^
                                    --memory="512m" ^
                                    -v retail-data:/app/data ^
                                    "${env.BUILD_IMAGE}"
                            """

                            echo "Production deployment started."
                        }

                        /*
                         * Final health check.
                         */
                        sleep 5

                        bat """
                            @echo off

                            echo ===== FINAL CONTAINER STATUS =====

                            "%DOCKER%" ps

                            echo.
                            echo ===== FINAL HEALTH =====

                            "%DOCKER%" inspect ^
                                --format="{{.State.Health.Status}}" ^
                                "${finalName}"
                        """

                    } catch (Exception deploymentError) {

                        echo "=========================================="
                        echo "DEPLOYMENT FAILED"
                        echo "STARTING AUTOMATIC ROLLBACK"
                        echo "=========================================="

                        /*
                         * Remove failed candidate.
                         */
                        bat """
                            @echo off

                            "%DOCKER%" rm -f "${candidateName}" >nul 2>&1 || exit /b 0
                        """

                        /*
                         * Only production has automatic rollback
                         * requirement.
                         */
                        if (params.ENVIRONMENT == 'PRODUCTION') {

                            def rollbackImage =
                                env.PREVIOUS_PRODUCTION_IMAGE

                            echo "Previous production image:"
                            echo "${rollbackImage}"

                            if (!rollbackImage ||
                                rollbackImage == 'NONE') {

                                echo "No previous production image exists."
                                echo "Rollback is not possible for first deployment."

                                bat """
                                    @echo off

                                    "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0
                                """

                            } else {

                                echo "Restoring production image:"
                                echo "${rollbackImage}"

                                bat """
                                    @echo off

                                    "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0

                                    "%DOCKER%" run -d ^
                                        --name retail-app-production ^
                                        --network "${env.NETWORK_NAME}" ^
                                        -p 8081:8081 ^
                                        -e APP_VERSION=4.2.1 ^
                                        -e APP_ENV=production ^
                                        -e PAYMENT_MODE=normal ^
                                        --cpus="1.0" ^
                                        --memory="512m" ^
                                        -v retail-data:/app/data ^
                                        "${rollbackImage}"
                                """

                                echo "Rollback container started."

                                /*
                                 * Verify rollback health properly.
                                 */
                                script {

                                    def rollbackHealthy = false

                                    for (int i = 1; i <= 12; i++) {

                                        sleep 5

                                        def rollbackHealth = bat(
                                            returnStdout: true,
                                            script: """
                                                @echo off

                                                "%DOCKER%" inspect ^
                                                    --format="{{.State.Health.Status}}" ^
                                                    retail-app-production
                                            """
                                        ).trim()

                                        echo "Rollback health check ${i}/12: ${rollbackHealth}"

                                        if (rollbackHealth == 'healthy') {
                                            rollbackHealthy = true
                                            break
                                        }

                                        if (rollbackHealth == 'unhealthy') {
                                            break
                                        }
                                    }

                                    if (!rollbackHealthy) {

                                        echo "=========================================="
                                        echo "AUTOMATIC ROLLBACK HEALTH CHECK FAILED"
                                        echo "=========================================="

                                        error(
                                            "Automatic rollback container did not become healthy."
                                        )
                                    }

                                    echo "=========================================="
                                    echo "AUTOMATIC ROLLBACK VERIFIED"
                                    echo "Production restored successfully."
                                    echo "Restored image: ${rollbackImage}"
                                    echo "=========================================="
                                }
                            }

                            echo "=========================================="
                            echo "FINAL STATE: DEPLOYMENT FAILED / ROLLBACK"
                            echo "=========================================="

                            error(
                                "Deployment failed. Automatic rollback process completed."
                            )

                        } else {

                            error(
                                "UAT deployment failed."
                            )
                        }
                    }
                }
            }
        }

        stage('Deployment Validation') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    def validationPort =
                        params.ENVIRONMENT == 'PRODUCTION'
                            ? '8081'
                            : '8082'

                    echo "=========================================="
                    echo "DEPLOYMENT VALIDATION"
                    echo "=========================================="

                    bat """
                        @echo off

                        echo ===== HEALTH API =====

                        curl -f http://localhost:${validationPort}/health

                        echo.
                        echo.
                        echo ===== VERSION API =====

                        curl -f http://localhost:${validationPort}/version

                        echo.
                        echo.
                        echo ===== PAYMENT API =====

                        curl -f http://localhost:${validationPort}/payment

                        echo.
                        echo.
                        echo ===== DOCKER CONTAINERS =====

                        "%DOCKER%" ps

                        echo.
                        echo ===== DOCKER IMAGE =====

                        "%DOCKER%" images "${env.IMAGE_REPOSITORY}"
                    """
                }
            }
        }
    }

    post {

        success {
            echo "=========================================="
            echo "JENKINS PIPELINE SUCCESS"
            echo "=========================================="

            echo "Version     : ${params.VERSION}"
            echo "Environment : ${params.ENVIRONMENT}"
            echo "Action      : ${params.DEPLOYMENT_ACTION}"
            echo "Image       : ${env.BUILD_IMAGE}"
            echo "Build       : ${env.BUILD_NUMBER}"
        }

        failure {
            echo "=========================================="
            echo "JENKINS PIPELINE FAILED"
            echo "=========================================="

            echo "Version     : ${params.VERSION}"
            echo "Environment : ${params.ENVIRONMENT}"
            echo "Action      : ${params.DEPLOYMENT_ACTION}"
            echo "Build       : ${env.BUILD_NUMBER}"

            echo "Check the console output for deployment/rollback details."
        }

        always {
            echo "=========================================="
            echo "FINAL DOCKER STATE"
            echo "=========================================="

            bat """
                @echo off

                "%DOCKER%" ps -a

                echo.
                echo ===== RETAIL APP IMAGES =====

                "%DOCKER%" images "${env.IMAGE_REPOSITORY}"
            """
        }
    }
}
```
