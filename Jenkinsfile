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
            description: 'Must be YES for production deployment'
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
                        params.DEPLOYMENT_ACTION == 'DEPLOY' &&
                        params.CONFIRM_PROD != 'YES') {

                        error("Production deployment blocked. CONFIRM_PROD must be YES.")
                    }

                    if (params.DEPLOYMENT_ACTION == 'ROLLBACK' &&
                        params.ENVIRONMENT != 'PRODUCTION') {

                        error("Rollback action is allowed only for PRODUCTION.")
                    }
                }
            }
        }

        stage('Checkout Requested Version') {
            steps {
                bat """
                    echo ==========================================
                    echo Fetching Git tags
                    echo ==========================================

                    git fetch --tags --force

                    echo.
                    echo Checking requested version:
                    echo ${params.VERSION}

                    git rev-parse --verify refs/tags/${params.VERSION}

                    echo.
                    echo Checking out requested tag:

                    git checkout --force tags/${params.VERSION}

                    echo.
                    echo Selected Git commit:

                    git rev-parse HEAD

                    echo.
                    echo Selected Git version:

                    git describe --tags --always --dirty

                    echo ==========================================
                """
            }
        }

        stage('Build Docker Image') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    env.IMAGE_TAG =
                        "${params.VERSION}-${env.BUILD_NUMBER}"

                    echo "Building Docker image:"
                    echo "${IMAGE_REPOSITORY}:${IMAGE_TAG}"

                    bat """
                        "${DOCKER}" build ^
                        -t ${IMAGE_REPOSITORY}:${IMAGE_TAG} .
                    """
                }
            }
        }

        stage('Create Docker Network') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                bat """
                    "${DOCKER}" network inspect ${NETWORK_NAME} >nul 2>&1

                    if errorlevel 1 (
                        echo Creating Docker network ${NETWORK_NAME}
                        "${DOCKER}" network create ${NETWORK_NAME}
                    ) else (
                        echo Docker network ${NETWORK_NAME} already exists
                    )
                """
            }
        }

        stage('Record Previous Production') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY' &&
                    params.ENVIRONMENT == 'PRODUCTION'
                }
            }

            steps {
                script {

                    def status = bat(
                        script: """
                            "${DOCKER}" inspect --format="{{.Config.Image}}" retail-app-production > previous-image.txt 2>nul
                        """,
                        returnStatus: true
                    )

                    if (status != 0) {
                        writeFile(
                            file: 'previous-image.txt',
                            text: 'NONE'
                        )
                    }

                    env.PREVIOUS_IMAGE =
                        readFile('previous-image.txt').trim()

                    if (!env.PREVIOUS_IMAGE) {
                        env.PREVIOUS_IMAGE = 'NONE'
                    }

                    echo "Previous production image: ${env.PREVIOUS_IMAGE}"
                }
            }
        }

        stage('Rollback Action') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'ROLLBACK'
                }
            }

            steps {
                script {

                    echo "=========================================="
                    echo "MANUAL PRODUCTION ROLLBACK"
                    echo "=========================================="

                    def rollbackImage =
                        'retail-app:4.2.1'

                    echo "Rollback image: ${rollbackImage}"

                    bat """
                        "${DOCKER}" rm -f retail-app-production 2>nul || exit /b 0

                        "${DOCKER}" run -d ^
                        --name retail-app-production ^
                        --network ${NETWORK_NAME} ^
                        -p 8081:8081 ^
                        -e APP_VERSION=4.2.1 ^
                        -e APP_ENV=production ^
                        -e PAYMENT_MODE=normal ^
                        ${rollbackImage}
                    """

                    echo "Waiting for rollback health check..."

                    bat """
                        powershell -NoProfile -Command ^
                        "\$healthy = \$false; ^
                        for (\$i=1; \$i -le 12; \$i++) { ^
                            Start-Sleep -Seconds 5; ^
                            \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' retail-app-production 2>`$null; ^
                            Write-Host ('Rollback health attempt ' + \$i + ': ' + \$status); ^
                            if (\$status -eq 'healthy') { \$healthy = \$true; break } ^
                        }; ^
                        if (-not \$healthy) { exit 1 }"
                    """

                    echo "MANUAL ROLLBACK VERIFIED"
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

                    def candidateName =
                        "retail-app-candidate-${env.BUILD_NUMBER}"

                    def finalName

                    def candidatePort
                    def finalPort

                    if (params.ENVIRONMENT == 'PRODUCTION') {

                        finalName = 'retail-app-production'
                        candidatePort = '8083'
                        finalPort = '8081'

                    } else {

                        finalName = 'retail-app-uat'
                        candidatePort = '8082'
                        finalPort = '8082'
                    }

                    env.CANDIDATE_NAME = candidateName
                    env.FINAL_NAME = finalName
                    env.CANDIDATE_PORT = candidatePort
                    env.FINAL_PORT = finalPort

                    echo "=========================================="
                    echo "DEPLOYMENT DETAILS"
                    echo "Candidate : ${candidateName}"
                    echo "Final     : ${finalName}"
                    echo "Image     : ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
                    echo "Candidate Port: ${candidatePort}"
                    echo "Final Port    : ${finalPort}"
                    echo "=========================================="

                    try {

                        echo "Starting candidate container..."

                        bat """
                            "${DOCKER}" rm -f ${candidateName} 2>nul || exit /b 0

                            "${DOCKER}" run -d ^
                            --name ${candidateName} ^
                            --network ${NETWORK_NAME} ^
                            -p ${candidatePort}:8081 ^
                            --cpus="1.0" ^
                            --memory="512m" ^
                            -e APP_VERSION=${params.VERSION} ^
                            -e APP_ENV=${params.ENVIRONMENT} ^
                            -e PAYMENT_MODE=normal ^
                            ${IMAGE_REPOSITORY}:${IMAGE_TAG}
                        """

                        echo "Waiting for candidate health check..."

                        bat """
                            powershell -NoProfile -Command ^
                            "\$healthy = \$false; ^
                            for (\$i=1; \$i -le 12; \$i++) { ^
                                Start-Sleep -Seconds 5; ^
                                \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${candidateName} 2>`$null; ^
                                Write-Host ('Candidate health attempt ' + \$i + ': ' + \$status); ^
                                if (\$status -eq 'healthy') { \$healthy = \$true; break }; ^
                                if (\$status -eq 'unhealthy') { break } ^
                            }; ^
                            if (-not \$healthy) { ^
                                Write-Host 'Candidate health check FAILED'; ^
                                exit 1 ^
                            }"
                        """

                        echo "Candidate health check PASSED"

                        echo "Stopping old production/UAT container if present..."

                        bat """
                            "${DOCKER}" rm -f ${finalName} 2>nul || exit /b 0
                        """

                        echo "Starting final container..."

                        bat """
                            "${DOCKER}" run -d ^
                            --name ${finalName} ^
                            --network ${NETWORK_NAME} ^
                            -p ${finalPort}:8081 ^
                            --cpus="1.0" ^
                            --memory="512m" ^
                            -e APP_VERSION=${params.VERSION} ^
                            -e APP_ENV=${params.ENVIRONMENT} ^
                            -e PAYMENT_MODE=normal ^
                            ${IMAGE_REPOSITORY}:${IMAGE_TAG}
                        """

                        echo "Removing candidate container..."

                        bat """
                            "${DOCKER}" rm -f ${candidateName} 2>nul || exit /b 0
                        """

                        echo "Waiting for final health check..."

                        bat """
                            powershell -NoProfile -Command ^
                            "\$healthy = \$false; ^
                            for (\$i=1; \$i -le 12; \$i++) { ^
                                Start-Sleep -Seconds 5; ^
                                \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${finalName} 2>`$null; ^
                                Write-Host ('Final health attempt ' + \$i + ': ' + \$status); ^
                                if (\$status -eq 'healthy') { \$healthy = \$true; break } ^
                            }; ^
                            if (-not \$healthy) { exit 1 }"
                        """

                        echo "=========================================="
                        echo "DEPLOYMENT SUCCESSFUL"
                        echo "Version: ${params.VERSION}"
                        echo "Image: ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
                        echo "Environment: ${params.ENVIRONMENT}"
                        echo "=========================================="
                    }

                    catch (err) {

                        echo "=========================================="
                        echo "DEPLOYMENT FAILED"
                        echo "Starting automatic rollback..."
                        echo "=========================================="

                        bat """
                            "${DOCKER}" rm -f ${candidateName} 2>nul || exit /b 0
                        """

                        if (params.ENVIRONMENT == 'PRODUCTION') {

                            if (env.PREVIOUS_IMAGE &&
                                env.PREVIOUS_IMAGE != 'NONE') {

                                echo "Restoring previous production image:"
                                echo "${env.PREVIOUS_IMAGE}"

                                bat """
                                    "${DOCKER}" rm -f ${finalName} 2>nul || exit /b 0

                                    "${DOCKER}" run -d ^
                                    --name ${finalName} ^
                                    --network ${NETWORK_NAME} ^
                                    -p 8081:8081 ^
                                    --cpus="1.0" ^
                                    --memory="512m" ^
                                    -e APP_VERSION=4.2.1 ^
                                    -e APP_ENV=production ^
                                    -e PAYMENT_MODE=normal ^
                                    ${env.PREVIOUS_IMAGE}
                                """

                                echo "Waiting for rollback health check..."

                                bat """
                                    powershell -NoProfile -Command ^
                                    "\$healthy = \$false; ^
                                    for (\$i=1; \$i -le 12; \$i++) { ^
                                        Start-Sleep -Seconds 5; ^
                                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${finalName} 2>`$null; ^
                                        Write-Host ('Rollback health attempt ' + \$i + ': ' + \$status); ^
                                        if (\$status -eq 'healthy') { \$healthy = \$true; break } ^
                                    }; ^
                                    if (-not \$healthy) { ^
                                        Write-Host 'Rollback health check FAILED'; ^
                                        exit 1 ^
                                    }"
                                """

                                echo "=========================================="
                                echo "AUTOMATIC ROLLBACK VERIFIED"
                                echo "Restored image: ${env.PREVIOUS_IMAGE}"
                                echo "=========================================="

                            } else {

                                echo "No previous production image was recorded."
                                echo "Automatic rollback could not restore an older image."

                                error(
                                    "Deployment failed and no previous production image was available."
                                )
                            }
                        }

                        error(
                            "Deployment failed. Automatic rollback process completed."
                        )
                    }
                }
            }
        }

        stage('Final Validation') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    def port

                    if (params.ENVIRONMENT == 'PRODUCTION') {
                        port = '8081'
                    } else {
                        port = '8082'
                    }

                    echo "=========================================="
                    echo "FINAL VALIDATION"
                    echo "Environment: ${params.ENVIRONMENT}"
                    echo "Port: ${port}"
                    echo "=========================================="

                    bat """
                        "${DOCKER}" ps
                    """

                    bat """
                        "${DOCKER}" inspect --format="{{.State.Health.Status}}" ${env.FINAL_NAME}
                    """

                    bat """
                        powershell -NoProfile -Command ^
                        "try { ^
                            \$response = Invoke-WebRequest -UseBasicParsing http://localhost:${port}/version; ^
                            Write-Host \$response.Content; ^
                        } catch { ^
                            Write-Host 'Application validation failed'; ^
                            exit 1 ^
                        }"
                    """
                }
            }
        }
    }

    post {

        always {

            echo "=========================================="
            echo "FINAL DOCKER STATE"
            echo "=========================================="

            bat """
                "${DOCKER}" ps -a
            """

            echo "=========================================="
            echo "DEPLOYMENT PIPELINE COMPLETED"
            echo "=========================================="
        }
    }
}