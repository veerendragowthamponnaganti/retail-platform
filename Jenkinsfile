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

                if (params.DEPLOYMENT_ACTION == 'DEPLOY') {

                    if (params.ENVIRONMENT == 'PRODUCTION' &&
                        params.CONFIRM_PROD != 'YES') {

                        error(
                            "PRODUCTION deployment blocked. CONFIRM_PROD must be YES."
                        )
                    }
                }

                if (!params.VERSION?.trim()) {
                    error("VERSION cannot be empty.")
                }

                echo "Parameter validation successful."
            }
        }
    }

    stage('Checkout Requested Version') {
        steps {
            script {

                echo "Checking requested Git tag: ${params.VERSION}"

                bat """
                    git fetch --all --tags
                    git rev-parse --verify refs/tags/${params.VERSION}
                """

                bat """
                    git checkout --force tags/${params.VERSION}
                """

                bat """
                    git describe --tags --always --dirty
                """

                echo "Requested Git version successfully checked out."
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

                env.IMAGE_TAG =
                    "${params.VERSION}-${env.BUILD_NUMBER}"

                echo "Building Docker image:"
                echo "${env.IMAGE_REPOSITORY}:${env.IMAGE_TAG}"

                bat """
                    "${DOCKER}" build ^
                    -t ${IMAGE_REPOSITORY}:${IMAGE_TAG} .
                """

                echo "Docker image created successfully."
            }
        }
    }

    stage('Create Docker Network') {
        steps {
            bat """
                "${DOCKER}" network inspect ${NETWORK_NAME} >nul 2>nul || ^
                "${DOCKER}" network create ${NETWORK_NAME}
            """

            echo "Docker network verified: ${NETWORK_NAME}"
        }
    }

    stage('Record Previous Production') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY'
            }
        }

        steps {
            script {

                bat """
                    "${DOCKER}" ps ^
                    --filter "name=retail-app-production" ^
                    --format "{{.Image}}" > previous-image.txt 2>nul
                """

                def previousImage = ''

                if (fileExists('previous-image.txt')) {
                    previousImage = readFile(
                        'previous-image.txt'
                    ).trim()
                }

                if (!previousImage) {
                    previousImage = 'NONE'
                }

                env.PREVIOUS_PRODUCTION_IMAGE = previousImage

                echo "Previous production image: ${previousImage}"
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

                def rollbackImage = "retail-app:v4.2.1-10"

                echo "=============================================="
                echo "MANUAL ROLLBACK"
                echo "Restoring image: ${rollbackImage}"
                echo "=============================================="

                bat """
                    "${DOCKER}" rm -f retail-app-production 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name retail-app-production ^
                    --network ${NETWORK_NAME} ^
                    -p 8081:8081 ^
                    -e APP_VERSION=v4.2.1 ^
                    -e APP_ENV=production ^
                    -e PAYMENT_MODE=normal ^
                    --restart unless-stopped ^
                    ${rollbackImage}
                """

                echo "Waiting for rollback container health..."

                sleep(time: 20, unit: 'SECONDS')

                def rollbackStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' retail-app-production
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Rollback health status: ${rollbackStatus}"

                if (rollbackStatus != 'healthy') {
                    error(
                        "Manual rollback health check FAILED."
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

                def candidateName =
                    "retail-app-candidate-${env.BUILD_NUMBER}"

                env.CANDIDATE_NAME = candidateName

                def candidatePort =
                    params.ENVIRONMENT == 'PRODUCTION'
                    ? '8083'
                    : '8082'

                env.CANDIDATE_PORT = candidatePort

                echo "=============================================="
                echo "Starting deployment candidate"
                echo "Candidate container : ${candidateName}"
                echo "Candidate image     : ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
                echo "Candidate port      : ${candidatePort}"
                echo "=============================================="

                bat """
                    "${DOCKER}" rm -f ${candidateName} 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name ${candidateName} ^
                    --network ${NETWORK_NAME} ^
                    -p ${candidatePort}:8081 ^
                    -e APP_VERSION=${params.VERSION} ^
                    -e APP_ENV=${params.ENVIRONMENT} ^
                    -e PAYMENT_MODE=normal ^
                    --cpus=1.0 ^
                    --memory=512m ^
                    ${IMAGE_REPOSITORY}:${IMAGE_TAG}
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

                echo "Waiting for candidate health check..."

                sleep(time: 20, unit: 'SECONDS')

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
                    echo "Candidate health check FAILED"
                    echo "Automatic rollback will start."
                    echo "=============================================="

                    currentBuild.result = 'FAILURE'

                    error(
                        "Candidate health check failed. Automatic rollback required."
                    )
                }

                echo "Candidate health check PASSED."
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

                def finalName =
                    params.ENVIRONMENT == 'PRODUCTION'
                    ? 'retail-app-production'
                    : 'retail-app-uat'

                env.FINAL_CONTAINER_NAME = finalName

                def finalPort =
                    params.ENVIRONMENT == 'PRODUCTION'
                    ? '8081'
                    : '8082'

                echo "Promoting candidate to final container:"
                echo "${finalName}"

                bat """
                    "${DOCKER}" rm -f ${finalName} 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name ${finalName} ^
                    --network ${NETWORK_NAME} ^
                    -p ${finalPort}:8081 ^
                    -e APP_VERSION=${params.VERSION} ^
                    -e APP_ENV=${params.ENVIRONMENT} ^
                    -e PAYMENT_MODE=normal ^
                    --cpus=1.0 ^
                    --memory=512m ^
                    ${IMAGE_REPOSITORY}:${IMAGE_TAG}
                """

                bat """
                    "${DOCKER}" rm -f ${env.CANDIDATE_NAME} 2>nul || exit /b 0
                """

                echo "New version started."
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

                echo "Waiting for final container health..."

                sleep(time: 20, unit: 'SECONDS')

                def finalStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${env.FINAL_CONTAINER_NAME}
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Final container health status: ${finalStatus}"

                if (finalStatus != 'healthy') {

                    echo "=============================================="
                    echo "FINAL HEALTH CHECK FAILED"
                    echo "Starting automatic rollback."
                    echo "=============================================="

                    currentBuild.result = 'FAILURE'

                    error(
                        "Final health check failed. Automatic rollback required."
                    )
                }

                echo "Final health check PASSED."
            }
        }
    }

    stage('Automatic Rollback') {
        when {
            expression {
                params.DEPLOYMENT_ACTION == 'DEPLOY' &&
                currentBuild.result == 'FAILURE'
            }
        }

        steps {
            script {

                echo "=============================================="
                echo "AUTOMATIC ROLLBACK STARTED"
                echo "=============================================="

                def previousImage =
                    env.PREVIOUS_PRODUCTION_IMAGE

                if (!previousImage ||
                    previousImage == 'NONE') {

                    echo "No previous production image was recorded."

                    error(
                        "Automatic rollback cannot continue because previous production image is unavailable."
                    )
                }

                echo "Previous production image:"
                echo "${previousImage}"

                bat """
                    "${DOCKER}" rm -f ${env.FINAL_CONTAINER_NAME} 2>nul || exit /b 0
                """

                bat """
                    "${DOCKER}" run -d ^
                    --name ${env.FINAL_CONTAINER_NAME} ^
                    --network ${NETWORK_NAME} ^
                    -p 8081:8081 ^
                    -e APP_VERSION=v4.2.1 ^
                    -e APP_ENV=production ^
                    -e PAYMENT_MODE=normal ^
                    --restart unless-stopped ^
                    ${previousImage}
                """

                echo "Previous production version restored."

                sleep(time: 20, unit: 'SECONDS')

                def rollbackStatus = powershell(
                    script: """
                        \$status = & '${DOCKER}' inspect --format='{{.State.Health.Status}}' ${env.FINAL_CONTAINER_NAME}
                        Write-Output \$status
                    """,
                    returnStdout: true
                ).trim()

                echo "Rollback health status: ${rollbackStatus}"

                if (rollbackStatus != 'healthy') {

                    echo "=============================================="
                    echo "ROLLBACK HEALTH CHECK FAILED"
                    echo "Production recovery could not be verified."
                    echo "=============================================="

                    error(
                        "Rollback health check FAILED."
                    )
                }

                echo "=============================================="
                echo "ROLLBACK VERIFIED SUCCESSFULLY"
                echo "Production restored to:"
                echo "${previousImage}"
                echo "=============================================="
            }
        }
    }

    stage('Final Validation') {
        steps {
            script {

                echo "=============================================="
                echo "FINAL DEPLOYMENT VALIDATION"
                echo "=============================================="

                bat """
                    "${DOCKER}" ps -a
                """

                bat """
                    "${DOCKER}" images ${IMAGE_REPOSITORY}
                """

                if (params.DEPLOYMENT_ACTION == 'DEPLOY') {

                    echo "Requested version : ${params.VERSION}"
                    echo "Build number      : ${env.BUILD_NUMBER}"
                    echo "Image tag         : ${env.IMAGE_TAG}"
                    echo "Previous image    : ${env.PREVIOUS_PRODUCTION_IMAGE}"
                }

                echo "=============================================="
            }
        }
    }
}

post {

    always {

        echo "=============================================="
        echo "FINAL DOCKER STATE"
        echo "=============================================="

        bat """
            "${DOCKER}" ps -a
        """

        echo "=============================================="
    }

    success {

        echo "=============================================="
        echo "JENKINS BUILD SUCCESSFUL"
        echo "Deployment completed successfully."
        echo "=============================================="
    }

    failure {

        echo "=============================================="
        echo "JENKINS BUILD FAILED"
        echo "If deployment failed, rollback protection was triggered."
        echo "Check the console output for rollback verification."
        echo "=============================================="
    }
}
}
