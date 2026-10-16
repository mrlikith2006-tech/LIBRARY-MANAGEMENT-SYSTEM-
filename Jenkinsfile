pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Test') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m unittest discover -s tests -v'
                    } else {
                        bat 'python -m unittest discover -s tests -v'
                    }
                }
            }
        }

        stage('Publish') {
            steps {
                archiveArtifacts(
                    artifacts: 'library_app.py,run_library.*,src/library_management/**,README.md',
                    fingerprint: true
                )
            }
        }
    }
}
