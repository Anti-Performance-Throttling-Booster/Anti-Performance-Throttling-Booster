pipeline {
    agent { label 'windows' }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        VENV = '.venv'
        PACKAGE = 'dist\\pulseboost-${BUILD_NUMBER}.zip'
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Install') {
            steps {
                bat 'py -3 -m venv %VENV%'
                bat '%VENV%\\Scripts\\python.exe -m pip install --upgrade pip'
                bat '%VENV%\\Scripts\\python.exe -m pip install -r requirements.txt pytest'
            }
        }
        stage('Static checks') {
            steps {
                bat '%VENV%\\Scripts\\python.exe -m compileall -q detection logging_module monitoring optimization dashboard.py'
            }
        }
        stage('Test') {
            steps {
                bat '%VENV%\\Scripts\\python.exe -m pytest -q --junitxml=test-results.xml'
            }
            post { always { junit allowEmptyResults: false, testResults: 'test-results.xml' } }
        }
        stage('Package') {
            steps {
                bat 'if not exist dist mkdir dist'
                bat 'powershell -NoProfile -Command "Get-ChildItem -Path detection,logging_module,monitoring,optimization -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force"'
                bat 'powershell -NoProfile -Command "Compress-Archive -Path detection,logging_module,monitoring,optimization,dashboard.py,requirements.txt,README.md -DestinationPath $env:PACKAGE -Force"'
                archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
            }
        }
        stage('Deploy') {
            when { branch 'main' }
            steps {
                // Configure PULSEBOOST_DEPLOY_DIR as a Jenkins credential/environment
                // variable on the Windows agent. Copying is atomic at file level and
                // keeps a numbered release for rollback.
                bat 'if "%PULSEBOOST_DEPLOY_DIR%"=="" (echo Deployment target is not configured & exit /b 1)'
                bat 'if not exist "%PULSEBOOST_DEPLOY_DIR%" mkdir "%PULSEBOOST_DEPLOY_DIR%"'
                bat 'copy /Y "%PACKAGE%" "%PULSEBOOST_DEPLOY_DIR%\\"'
            }
        }
    }
    post {
        success { echo 'Build, verification, package, and main-branch deployment completed.' }
        failure { echo 'Pipeline failed; deployment was not marked successful.' }
        always { cleanWs(deleteDirs: true, notFailBuild: true) }
    }
}
