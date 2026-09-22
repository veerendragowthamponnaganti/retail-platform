pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOYMENT_ACTION',
            choices: ['DEPLOY', 'ROLLBACK'],
            description: 'Select deployment action'
        )

        choice(
            name: 'ENVIRONMENT',
            choices: ['UAT', 'PRODUCTION'],
            description: 'Select deployment environment'
        )

        string(
            name: 'VERSION',
            defaultValue: 'v4.2.1',
            description: 'Git tag to deploy, for example v4.2.1'
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

        stage('Validate Parameters') {
            steps {
                script {
                    echo "========================================"
                    echo "Deployment Action : ${params.DEPLOYMENT_ACTION}"
                    echo "Environment       : ${params.ENVIRONMENT}"
                    echo "Requested Version : ${params.VERSION}"
                    echo "Production Confirm : ${params.CONFIRM_PROD}"
                    echo "========================================"

                    if (!params.VERSION?.trim()) {
                        error("VERSION cannot be empty.")
                    }

                    if (params.ENVIRONMENT == 'PRODUCTION' &&
                        params.CONFIRM_PROD != 'YES') {

                        error(
                            "Production deployment blocked. " +
                            "CONFIRM_PROD must be YES."
                        )
                    }
                }
            }
        }

        stage('Checkout Requested Version') {
            steps {
                script {

                    def version = params.VERSION

                    bat """
                        echo Fetching Git tags...

                        git fetch --tags --force

                        echo.

                        echo Validating requested tag:

                        git rev-parse --verify refs/tags/${version}

                        if errorlevel 1 (
                            echo Requested Git tag ${version} does not exist.
                            exit /b 1
                        )

                        echo.

                        echo Checking out requested version:

                        git checkout --force tags/${version}

                        echo.

                        echo Selected Git commit:

                        git rev-parse HEAD

                        echo.

                        echo Selected Git commit details:

                        git log -1 --oneline
                    """
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

                    def version = params.VERSION
                    def imageTag = "${version}-${env.BUILD_NUMBER}"

                    bat """
                        echo Checking Docker...

                        "%DOCKER%" --version

                        echo.

                        echo Creating Docker network if required...

                        "%DOCKER%" network inspect %NETWORK_NAME% >nul 2>&1 || "%DOCKER%" network create %NETWORK_NAME%

                        echo.

                        echo Building Docker image:

                        echo ${env.IMAGE_REPOSITORY}:${imageTag}

                        "%DOCKER%" build ^
                            -t ${env.IMAGE_REPOSITORY}:${imageTag} ^
                            .

                        if errorlevel 1 (
                            echo Docker image build failed.
                            exit /b 1
                        )

                        echo.

                        echo Docker image created:

                        "%DOCKER%" images %IMAGE_REPOSITORY%
                    """
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

                    def previousImage = bat(
                        returnStdout: true,
                        script: '''
                            @echo off
                            "%DOCKER%" inspect --format="{{.Config.Image}}" retail-app-production 2>nul || echo NONE
                        '''
                    ).trim()

                    env.PREVIOUS_PRODUCTION_IMAGE = previousImage

                    echo "Previous production image: ${env.PREVIOUS_PRODUCTION_IMAGE}"
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

                    if (params.ENVIRONMENT != 'PRODUCTION') {
                        error("ROLLBACK is supported only for PRODUCTION.")
                    }

                    def previousImage =
                        env.PREVIOUS_PRODUCTION_IMAGE ?: 'retail-app:4.2.1'

                    echo "========================================"
                    echo "MANUAL ROLLBACK REQUESTED"
                    echo "Restoring image: ${previousImage}"
                    echo "========================================"

                    bat """
                        "%DOCKER%" network inspect %NETWORK_NAME% >nul 2>&1 || "%DOCKER%" network create %NETWORK_NAME%

                        "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0

                        "%DOCKER%" run -d ^
                            --name retail-app-production ^
                            --network %NETWORK_NAME% ^
                            -p 8081:8081 ^
                            --cpus 1 ^
                            --memory 512m ^
                            -e APP_VERSION=4.2.1 ^
                            -e APP_ENV=production ^
                            ${previousImage}
                    """

                    echo "Rollback container started."

                    powershell '''
                        $container = "retail-app-production"
                        $docker = $env:DOCKER

                        for ($i = 1; $i -le 12; $i++) {

                            $status = & $docker inspect --format="{{.State.Health.Status}}" $container 2>$null

                            Write-Host "Rollback health check attempt $i : $status"

                            if ($status -eq "healthy") {
                                Write-Host "Rollback successful."
                                exit 0
                            }

                            if ($status -eq "unhealthy") {
                                Write-Host "Rollback container is unhealthy."
                                exit 1
                            }

                            Start-Sleep -Seconds 5
                        }

                        Write-Host "Rollback health check timed out."
                        exit 1
                    '''

                    echo "========================================"
                    echo "ROLLBACK VERIFIED SUCCESSFULLY"
                    echo "========================================"
                }
            }
        }

        stage('Deploy and Health Check') {
            when {
                expression {
                    params.DEPLOYMENT_ACTION == 'DEPLOY'
                }
            }

            steps {
                script {

                    def version = params.VERSION
                    def environment = params.ENVIRONMENT

                    def hostPort =
                        environment == 'PRODUCTION'
                        ? '8081'
                        : '8082'

                    def candidateName =
                        "retail-app-candidate-${env.BUILD_NUMBER}"

                    def productionName =
                        environment == 'PRODUCTION'
                        ? 'retail-app-production'
                        : 'retail-app-uat'

                    def image =
                        "${env.IMAGE_REPOSITORY}:${version}-${env.BUILD_NUMBER}"

                    def previousImage =
                        env.PREVIOUS_PRODUCTION_IMAGE ?: 'NONE'

                    try {

                        echo "========================================"
                        echo "STARTING DEPLOYMENT"
                        echo "New image      : ${image}"
                        echo "Environment    : ${environment}"
                        echo "Candidate      : ${candidateName}"
                        echo "========================================"

                        /*
                         * Start candidate container.
                         * UAT uses port 8082.
                         * Production uses port 8081.
                         */
                        bat """
                            "%DOCKER%" rm -f ${candidateName} >nul 2>&1 || exit /b 0

                            "%DOCKER%" run -d ^
                                --name ${candidateName} ^
                                --network %NETWORK_NAME% ^
                                -p ${hostPort}:8081 ^
                                --cpus 1 ^
                                --memory 512m ^
                                -e APP_VERSION=${version} ^
                                -e APP_ENV=${environment} ^
                                ${image}

                            if errorlevel 1 (
                                echo Failed to start candidate container.
                                exit /b 1
                            )
                        """

                        echo "Candidate container started."
                        echo "Waiting for Docker health check..."

                        powershell """
                            \$container = '${candidateName}'
                            \$docker = \$env:DOCKER

                            for (\$i = 1; \$i -le 12; \$i++) {

                                \$status = & \$docker inspect --format='{{.State.Health.Status}}' \$container 2>\$null

                                Write-Host "Health check attempt \$i : \$status"

                                if (\$status -eq 'healthy') {
                                    Write-Host 'Candidate is healthy.'
                                    exit 0
                                }

                                if (\$status -eq 'unhealthy') {
                                    Write-Host 'Candidate is unhealthy.'
                                    exit 1
                                }

                                Start-Sleep -Seconds 5
                            }

                            Write-Host 'Health check timed out.'
                            exit 1
                        """

                        echo "Candidate health check passed."

                        /*
                         * PRODUCTION DEPLOYMENT
                         */
                        if (environment == 'PRODUCTION') {

                            echo "Previous production image: ${previousImage}"

                            echo "Removing old production container only after new version is healthy."

                            bat """
                                "%DOCKER%" rm -f ${productionName} >nul 2>&1 || exit /b 0
                            """

                            /*
                             * Candidate is healthy.
                             * Remove candidate before starting production
                             * because production will use port 8081.
                             */
                            bat """
                                "%DOCKER%" rm -f ${candidateName} >nul 2>&1

                                "%DOCKER%" run -d ^
                                    --name ${productionName} ^
                                    --network %NETWORK_NAME% ^
                                    -p 8081:8081 ^
                                    --cpus 1 ^
                                    --memory 512m ^
                                    -e APP_VERSION=${version} ^
                                    -e APP_ENV=production ^
                                    ${image}

                                if errorlevel 1 (
                                    echo Failed to start production container.
                                    exit /b 1
                                )
                            """

                        /*
                         * UAT DEPLOYMENT
                         */
                        } else {

                            echo "Candidate is healthy. Promoting candidate to UAT."

                            /*
                             * Remove any previous UAT container.
                             */
                            bat """
                                "%DOCKER%" rm -f ${productionName} >nul 2>&1 || exit /b 0
                            """

                            /*
                             * IMPORTANT:
                             * Candidate is currently using port 8082.
                             * Remove candidate before starting final UAT container.
                             */
                            bat """
                                "%DOCKER%" rm -f ${candidateName} >nul 2>&1
                            """

                            /*
                             * Start final UAT container on port 8082.
                             */
                            bat """
                                "%DOCKER%" run -d ^
                                    --name ${productionName} ^
                                    --network %NETWORK_NAME% ^
                                    -p 8082:8081 ^
                                    --cpus 1 ^
                                    --memory 512m ^
                                    -e APP_VERSION=${version} ^
                                    -e APP_ENV=uat ^
                                    ${image}

                                if errorlevel 1 (
                                    echo Failed to start UAT container.
                                    exit /b 1
                                )
                            """
                        }

                        echo "Final container started."

                        /*
                         * Final health check
                         */
                        powershell """
                            \$container = '${productionName}'
                            \$docker = \$env:DOCKER

                            for (\$i = 1; \$i -le 12; \$i++) {

                                \$status = & \$docker inspect --format='{{.State.Health.Status}}' \$container 2>\$null

                                Write-Host "Final health check attempt \$i : \$status"

                                if (\$status -eq 'healthy') {
                                    Write-Host 'Final container is healthy.'
                                    exit 0
                                }

                                if (\$status -eq 'unhealthy') {
                                    Write-Host 'Final container is unhealthy.'
                                    exit 1
                                }

                                Start-Sleep -Seconds 5
                            }

                            Write-Host 'Final health check timed out.'
                            exit 1
                        """

                        echo "========================================"
                        echo "DEPLOYMENT SUCCESSFUL"
                        echo "Version : ${version}"
                        echo "Image   : ${image}"
                        echo "========================================"

                    } catch (Exception deploymentError) {

                        echo "========================================"
                        echo "DEPLOYMENT FAILED"
                        echo "STARTING AUTOMATIC ROLLBACK"
                        echo "========================================"

                        /*
                         * Remove failed candidate container.
                         */
                        bat """
                            "%DOCKER%" rm -f ${candidateName} >nul 2>&1 || exit /b 0
                        """

                        /*
                         * Automatic rollback is required only for
                         * production when a previous image exists.
                         */
                        if (environment == 'PRODUCTION' &&
                            previousImage != 'NONE' &&
                            previousImage != '') {

                            echo "Restoring previous production image:"
                            echo "${previousImage}"

                            bat """
                                "%DOCKER%" rm -f retail-app-production >nul 2>&1 || exit /b 0

                                "%DOCKER%" run -d ^
                                    --name retail-app-production ^
                                    --network %NETWORK_NAME% ^
                                    -p 8081:8081 ^
                                    --cpus 1 ^
                                    --memory 512m ^
                                    -e APP_VERSION=4.2.1 ^
                                    -e APP_ENV=production ^
                                    ${previousImage}
                            """

                            powershell '''
                                $container = "retail-app-production"
                                $docker = $env:DOCKER

                                for ($i = 1; $i -le 12; $i++) {

                                    $status = & $docker inspect --format="{{.State.Health.Status}}" $container 2>$null

                                    Write-Host "Rollback health check attempt $i : $status"

                                    if ($status -eq "healthy") {
                                        Write-Host "Rollback successful."
                                        exit 0
                                    }

                                    if ($status -eq "unhealthy") {
                                        Write-Host "Rollback container is unhealthy."
                                        exit 1
                                    }

                                    Start-Sleep -Seconds 5
                                }

                                Write-Host "Rollback health check timed out."
                                exit 1
                            '''

                            echo "Rollback verified successfully."

                        } else {

                            echo "No previous production image was available for rollback."
                        }

                        error(
                            "Deployment failed. Automatic rollback process completed."
                        )
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

                    bat """
                        echo Running final API validation...

                        curl --fail http://localhost:${validationPort}/health

                        echo.

                        echo Version endpoint:

                        curl --fail http://localhost:${validationPort}/version

                        echo.

                        echo Running container status:

                        "%DOCKER%" ps
                    """
                }
            }
        }
    }

    post {

        success {
            echo "========================================"
            echo "FINAL STATE: DEPLOYMENT SUCCESSFUL"
            echo "VERSION: ${params.VERSION}"
            echo "ENVIRONMENT: ${params.ENVIRONMENT}"
            echo "========================================"
        }

        failure {
            echo "========================================"
            echo "FINAL STATE: DEPLOYMENT FAILED / ROLLBACK"
            echo "VERSION: ${params.VERSION}"
            echo "ENVIRONMENT: ${params.ENVIRONMENT}"
            echo "========================================"
        }

        always {
            echo "========================================"
            echo "Jenkins build number: ${env.BUILD_NUMBER}"
            echo "Jenkins result: ${currentBuild.currentResult}"
            echo "========================================"
        }
    }
}