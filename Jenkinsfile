pipeline {
agent any

```
parameters {
    choice(
        name: 'DEPLOYMENT_ACTION',
        choices: ['DEPLOY', 'ROLLBACK'],
        description: 'Select whether to deploy a new version or rollback production'
    )

    choice(
        name: 'ENVIRONMENT',
        choices: ['UAT', 'PRODUCTION'],
        description: 'Select deployment environment'
    )

    string(
        name: 'VERSION',
        defaultValue: 'v4.2.1',
        description: 'Git tag/version to deploy, for example v4.2.1 or v4.2.2'
    )

    choice(
        name: 'CONFIRM_PROD',
        choices: ['NO', 'YES'],
        description: 'Production deployment confirmation'
    )
}

environment {
    DOCKER = 'C:\\Users\\ASUS\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe'
    NETWORK_NAME = 'retail-network'
    PRODUCTION_CONTAINER = 'retail-app-production'
    CANDIDATE_PORT = '8083'
    PRODUCTION_PORT = '8081'
    CANDIDATE_NAME = "retail-app-candidate-${BUILD_NUMBER}"
    IMAGE_NAME = 'retail-app'
}

stages {

    stage('Show Parameters') {
        steps {
            echo "=============================================="
            echo "Retail Platform Deployment"
            echo "=============================================="
            echo "Deployment Action : ${params.DEPLOYMENT_ACTION}"
            echo "Environment       : ${params.ENVIRONMENT}"
            echo "Requested Version : ${params.VERSION}"
            echo "Production Confirm: ${params.CONFIRM_PROD}"
            echo "Build Number      : ${env.BUILD_NUMBER}"
            echo "=============================================="
        }
    }

    stage('Validate Parameters') {
        steps {
            script {

                if (!params.VERSION?.trim()) {
                    error("VERSION cannot be empty.")
                }

                if (params.ENVIRONMENT == 'PRODUCTION' &&
                    params.DEPLOYMENT_ACTION == 'DEPLOY' &&
                    params.CONFIRM_PROD != 'YES') {

                    error(
                        "Production deployment blocked. CONFIRM_PROD must be YES."
                    )
                }

                echo "Parameter validation passed."
            }
        }
    }

    stage('Checkout Requested Version') {
        steps {
            script {

                echo "Fetching latest Git references..."

                bat """
                    git fetch --all --tags --prune
                """

                echo "Checking whether requested version exists..."

                def tagCheck = bat(
                    script: """
                        git rev-parse --verify refs/tags/${params.VERSION}
                    """,
                    returnStatus: true
                )

                if (tagCheck != 0) {
                    error(
                        "Requested Git tag ${params.VERSION} does not exist."
                    )
                }

                echo "Requested Git tag exists."

                bat """
                    git checkout --force tags/${params.VERSION}
                """

                def selectedCommit = powershell(
                    script: """
                        git rev-parse HEAD
                    """,
                    returnStdout: true
                ).trim()

                env.SELECTED_COMMIT = selectedCommit

                echo "=============================================="
                echo "Selected Git Version : ${params.VERSION}"
                echo "Selected Git Commit  : ${selectedCommit}"
                echo "=============================================="
            }
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

                env.DEPLOY_IMAGE =
                    "${IMAGE_NAME}:${params.VERSION}-${BUILD_NUMBER}"

                echo "Building Docker image:"
                echo "${env.DEPLOY_IMAGE}"

                bat """
                    "${DOCKER}" build ^
                    -t ${env.DEPLOY_IMAGE} ^
                    .
                """

                echo "Docker image created successfully."

                powershell """
                    & '${DOCKER}' images ${IMAGE_NAME}
                """
            }
        }
    }

    stage('Create Docker Network') {
        steps {
            script {

                def networkStatus = bat(
                    script: """
                        "${DOCKER}" network inspect ${NETWORK_NAME} >nul 2>&1
                    """,
                    returnStatus: true
                )

                if (networkStatus != 0) {

                    echo "Docker network does not exist."
                    echo "Creating ${NETWORK_NAME}..."

                    bat """
                        "${DOCKER}" network create ${NETWORK_NAME}
                    """
                }
                else {
                    echo "Docker network ${NETWORK_NAME} already exists."
                }
            }
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

                echo "Checking current production container..."

                def productionExists = bat(
                    script: """
                        "${DOCKER}" inspect ${PRODUCTION_CONTAINER} >nul 2>&1
                    """,
                    returnStatus: true
                )

                if (productionExists == 0) {

                    def previousImage = powershell(
                        script: """
                            & '${DOCKER}' inspect --format='{{.Config.Image}}' ${PRODUCTION_CONTAINER}
                        """,
                        returnStdout: true
                    ).trim()

                    env.PREVIOUS_PRODUCTION_IMAGE =
                        previousImage

                    echo "=============================================="
                    echo "Previous Production Image:"
                    echo "${previousImage}"
                    echo "=============================================="
                }
                else {

                    env.PREVIOUS_PRODUCTION_IMAGE = 'NONE'

                    echo "No existing production container found."
                }
            }
        }
    }

    stage('Manual Rollback') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'ROLLBACK'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "MANUAL ROLLBACK REQUESTED"
                echo "=============================================="

                def rollbackImage = "${IMAGE_NAME}:v4.2.1-22"

                echo "Rollback image:"
                echo "${rollbackImage}"

                def imageExists = bat(
                    script: """
                        "${DOCKER}" image inspect ${rollbackImage} >nul 2>&1
                    """,
                    returnStatus: true
                )

                if (imageExists != 0) {
                    error(
                        "Rollback image ${rollbackImage} was not found."
                    )
                }

                bat """
                    "${DOCKER}" rm -f ${PRODUCTION_CONTAINER} 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name ${PRODUCTION_CONTAINER} ^
                    --network ${NETWORK_NAME} ^
                    -p ${PRODUCTION_PORT}:8081 ^
                    -e APP_VERSION=v4.2.1 ^
                    -e APP_ENV=production ^
                    -e PAYMENT_MODE=normal ^
                    --cpus=1.0 ^
                    --memory=512m ^
                    --restart unless-stopped ^
                    ${rollbackImage}
                """

                echo "Rollback container started."

                sleep(
                    time: 20,
                    unit: 'SECONDS'
                )

                def rollbackStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${PRODUCTION_CONTAINER}
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Rollback health status: ${rollbackStatus}"

                if (rollbackStatus != 'healthy') {
                    error(
                        "Manual rollback health check failed."
                    )
                }

                echo "Manual rollback verified successfully."
            }
        }
    }

    stage('Deploy Candidate') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "Starting Candidate Deployment"
                echo "=============================================="

                echo "Candidate container:"
                echo "${env.CANDIDATE_NAME}"

                echo "Candidate image:"
                echo "${env.DEPLOY_IMAGE}"

                bat """
                    "${DOCKER}" rm -f ${env.CANDIDATE_NAME} 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name ${env.CANDIDATE_NAME} ^
                    --network ${NETWORK_NAME} ^
                    -p ${CANDIDATE_PORT}:8081 ^
                    -e APP_VERSION=${params.VERSION} ^
                    -e APP_ENV=${params.ENVIRONMENT.toLowerCase()} ^
                    -e PAYMENT_MODE=normal ^
                    --cpus=1.0 ^
                    --memory=512m ^
                    ${env.DEPLOY_IMAGE}
                """

                echo "Candidate container started."
            }
        }
    }

    stage('Candidate Health Check') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "Candidate Health Check"
                echo "=============================================="

                echo "Waiting for candidate health status..."

                sleep(
                    time: 20,
                    unit: 'SECONDS'
                )

                def candidateStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${env.CANDIDATE_NAME}
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Candidate health status: ${candidateStatus}"

                if (candidateStatus != 'healthy') {

                    echo "=============================================="
                    echo "CANDIDATE HEALTH CHECK FAILED"
                    echo "=============================================="

                    echo "Automatic rollback will start immediately."

                    currentBuild.result = 'FAILURE'

                    def previousImage =
                        env.PREVIOUS_PRODUCTION_IMAGE

                    if (!previousImage ||
                        previousImage == 'NONE') {

                        error(
                            "Candidate failed and previous production image is unavailable."
                        )
                    }

                    echo "Previous production image:"
                    echo "${previousImage}"

                    echo "Stopping failed candidate..."

                    bat """
                        "${DOCKER}" rm -f ${env.CANDIDATE_NAME} 2>nul || exit /b 0
                    """

                    echo "Failed candidate removed."

                    echo "Removing current production container..."

                    bat """
                        "${DOCKER}" rm -f ${PRODUCTION_CONTAINER} 2>nul || exit /b 0
                    """

                    echo "Restoring previous production image..."

                    bat """
                        "${DOCKER}" run -d ^
                        --name ${PRODUCTION_CONTAINER} ^
                        --network ${NETWORK_NAME} ^
                        -p ${PRODUCTION_PORT}:8081 ^
                        -e APP_VERSION=v4.2.1 ^
                        -e APP_ENV=production ^
                        -e PAYMENT_MODE=normal ^
                        --cpus=1.0 ^
                        --memory=512m ^
                        --restart unless-stopped ^
                        ${previousImage}
                    """

                    echo "Previous production version restored."

                    echo "Waiting for rollback health check..."

                    sleep(
                        time: 20,
                        unit: 'SECONDS'
                    )

                    def rollbackStatus = powershell(
                        script: """
                            \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${PRODUCTION_CONTAINER}
                            Write-Output \$status
                        """,
                        returnStdout: true
                    ).trim()

                    echo "Rollback health status: ${rollbackStatus}"

                    if (rollbackStatus != 'healthy') {

                        echo "=============================================="
                        echo "ROLLBACK HEALTH CHECK FAILED"
                        echo "=============================================="

                        error(
                            "Deployment failed and rollback health check failed."
                        )
                    }

                    echo "=============================================="
                    echo "ROLLBACK VERIFIED SUCCESSFULLY"
                    echo "=============================================="

                    echo "Production restored to:"
                    echo "${previousImage}"

                    echo "Production health:"
                    echo "${rollbackStatus}"

                    error(
                        "Deployment failed as expected. Automatic rollback completed successfully."
                    )
                }

                echo "=============================================="
                echo "CANDIDATE HEALTH CHECK PASSED"
                echo "=============================================="
            }
        }
    }

    stage('Promote Candidate') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "Promoting Candidate to Production"
                echo "=============================================="

                if (params.ENVIRONMENT == 'PRODUCTION') {

                    echo "Production deployment confirmed."

                    echo "Stopping existing production container..."

                    bat """
                        "${DOCKER}" rm -f ${PRODUCTION_CONTAINER} 2>nul || exit /b 0
                    """

                    echo "Starting production using new image..."

                    bat """
                        "${DOCKER}" run -d ^
                        --name ${PRODUCTION_CONTAINER} ^
                        --network ${NETWORK_NAME} ^
                        -p ${PRODUCTION_PORT}:8081 ^
                        -e APP_VERSION=${params.VERSION} ^
                        -e APP_ENV=production ^
                        -e PAYMENT_MODE=normal ^
                        --cpus=1.0 ^
                        --memory=512m ^
                        --restart unless-stopped ^
                        ${env.DEPLOY_IMAGE}
                    """

                    echo "New production version started."

                    bat """
                        "${DOCKER}" rm -f ${env.CANDIDATE_NAME} 2>nul || exit /b 0
                    """

                    echo "Candidate container removed after promotion."
                }
                else {

                    echo "UAT deployment selected."

                    bat """
                        "${DOCKER}" rm -f retail-app-uat 2>nul || exit /b 0
                    """

                    bat """
                        "${DOCKER}" run -d ^
                        --name retail-app-uat ^
                        --network ${NETWORK_NAME} ^
                        -p 8081:8081 ^
                        -e APP_VERSION=${params.VERSION} ^
                        -e APP_ENV=uat ^
                        -e PAYMENT_MODE=normal ^
                        --cpus=1.0 ^
                        --memory=512m ^
                        --restart unless-stopped ^
                        ${env.DEPLOY_IMAGE}
                    """

                    bat """
                        "${DOCKER}" rm -f ${env.CANDIDATE_NAME} 2>nul || exit /b 0
                    """

                    echo "UAT deployment completed."
                }
            }
        }
    }

    stage('Final Health Check') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "Final Deployment Health Check"
                echo "=============================================="

                sleep(
                    time: 20,
                    unit: 'SECONDS'
                )

                def finalContainer =
                    params.ENVIRONMENT == 'PRODUCTION'
                    ? PRODUCTION_CONTAINER
                    : 'retail-app-uat'

                def finalStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${finalContainer}
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Final container:"
                echo "${finalContainer}"

                echo "Final health status:"
                echo "${finalStatus}"

                if (finalStatus != 'healthy') {

                    echo "FINAL HEALTH CHECK FAILED."

                    if (params.ENVIRONMENT == 'PRODUCTION' &&
                        env.PREVIOUS_PRODUCTION_IMAGE &&
                        env.PREVIOUS_PRODUCTION_IMAGE != 'NONE') {

                        echo "Emergency rollback starting..."

                        bat """
                            "${DOCKER}" rm -f ${PRODUCTION_CONTAINER} 2>nul || exit /b 0
                        """

                        bat """
                            "${DOCKER}" run -d ^
                            --name ${PRODUCTION_CONTAINER} ^
                            --network ${NETWORK_NAME} ^
                            -p ${PRODUCTION_PORT}:8081 ^
                            -e APP_VERSION=v4.2.1 ^
                            -e APP_ENV=production ^
                            -e PAYMENT_MODE=normal ^
                            --cpus=1.0 ^
                            --memory=512m ^
                            --restart unless-stopped ^
                            ${env.PREVIOUS_PRODUCTION_IMAGE}
                        """

                        sleep(
                            time: 20,
                            unit: 'SECONDS'
                        )

                        def emergencyRollbackStatus = powershell(
                            script: """
                                \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${PRODUCTION_CONTAINER}
                                Write-Output \$status
                            """,
                            returnStdout: true
                        ).trim()

                        echo "Emergency rollback health:"
                        echo "${emergencyRollbackStatus}"

                        if (emergencyRollbackStatus != 'healthy') {
                            error(
                                "Final health failed and emergency rollback failed."
                            )
                        }

                        error(
                            "Final health check failed. Emergency rollback completed successfully."
                        )
                    }

                    error(
                        "Final health check failed."
                    )
                }

                echo "=============================================="
                echo "FINAL HEALTH CHECK PASSED"
                echo "=============================================="
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

                echo "=============================================="
                echo "Final Deployment Validation"
                echo "=============================================="

                def validationContainer =
                    params.ENVIRONMENT == 'PRODUCTION'
                    ? PRODUCTION_CONTAINER
                    : 'retail-app-uat'

                powershell """
                    & '${DOCKER}' ps
                """

                powershell """
                    & '${DOCKER}' inspect ${validationContainer}
                """

                echo "Deployment validation completed."

                echo "Selected Git commit:"
                echo "${env.SELECTED_COMMIT}"

                echo "Requested version:"
                echo "${params.VERSION}"

                echo "Docker image:"
                echo "${env.DEPLOY_IMAGE}"
            }
        }
    }

    stage('Automatic Rollback') {
        when {
            expression {
                false
            }
        }

        steps {
            echo "Automatic rollback is handled inside Candidate Health Check."
        }
    }
}

post {

    always {

        echo "=============================================="
        echo "POST DEPLOYMENT INFORMATION"
        echo "=============================================="

        echo "Build Number:"
        echo "${env.BUILD_NUMBER}"

        echo "Requested Version:"
        echo "${params.VERSION}"

        echo "Deployment Action:"
        echo "${params.DEPLOYMENT_ACTION}"

        echo "Environment:"
        echo "${params.ENVIRONMENT}"

        echo "Selected Commit:"
        echo "${env.SELECTED_COMMIT}"

        echo "Previous Production Image:"
        echo "${env.PREVIOUS_PRODUCTION_IMAGE}"

        echo "=============================================="

        powershell """
            & '${DOCKER}' ps -a
        """

        echo "Docker images currently available:"

        powershell """
            & '${DOCKER}' images ${IMAGE_NAME}
        """
    }

    success {

        echo "=============================================="
        echo "JENKINS BUILD SUCCESSFUL"
        echo "=============================================="

        echo "Deployment completed successfully."

        echo "Version:"
        echo "${params.VERSION}"

        echo "Commit:"
        echo "${env.SELECTED_COMMIT}"
    }

    failure {

        echo "=============================================="
        echo "JENKINS BUILD FAILED"
        echo "=============================================="

        echo "Candidate health failure triggers immediate automatic rollback."

        echo "Production state can be verified from Docker output above."

        echo "=============================================="
    }
}
```

}
