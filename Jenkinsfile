// Phase 5: the same checks as .github/workflows/ci.yml, run by the local Jenkins in jenkins/.
// Start it with:  docker compose --profile ci up -d --build   →  http://localhost:8090 (admin / admin)
// More in jenkins/README.md.
// The tools (Python 3.12 via uv, Node 22, Java 21, Maven, kubeconform) are built into the
// Jenkins image, and the database tests use the jenkins-db service, so no Docker socket is needed.

pipeline {
  agent any

  options {
    timestamps()
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  triggers {
    // Check GitHub for new commits every 5 minutes (active after the first build).
    pollSCM('H/5 * * * *')
  }

  environment {
    TEST_DATABASE_URL = 'postgresql://dataguard:dataguard@jenkins-db:5432/dataguard'
    REPORTS = "${env.WORKSPACE}/reports"
    npm_config_cache = "${env.JENKINS_HOME}/.cache/npm"
    UV_CACHE_DIR = "${env.JENKINS_HOME}/.cache/uv"
    MAVEN_OPTS = "-Dmaven.repo.local=${env.JENKINS_HOME}/.m2/repository"
    FASTEMBED_CACHE_PATH = "${env.JENKINS_HOME}/.cache/fastembed"
  }

  stages {
    stage('Prepare') {
      steps {
        sh 'rm -rf reports && mkdir -p reports'
        sh 'uv --version && node --version && java -version 2>&1 | head -1 && mvn -v | head -1 && kubeconform -v'
      }
    }

    stage('Rules engine') {
      steps {
        dir('rules-engine') {
          sh '''
            uv venv --clear --python 3.12 --quiet .venv
            uv pip install --python .venv --quiet -r requirements-dev.txt -r ../db/requirements.txt
            .venv/bin/ruff check .
            .venv/bin/pytest -v --junitxml="$REPORTS/rules-engine.xml" -o junit_suite_name=rules-engine
          '''
        }
      }
    }

    stage('Agent') {
      steps {
        dir('agent') {
          sh '''
            uv venv --clear --python 3.12 --quiet .venv
            uv pip install --python .venv --quiet -r requirements-dev.txt
            .venv/bin/ruff check .
            .venv/bin/pytest -v --junitxml="$REPORTS/agent.xml" -o junit_suite_name=agent
          '''
        }
      }
    }

    stage('MCP server') {
      steps {
        dir('mcp-server') {
          sh '''
            npm ci --no-audit --no-fund
            npm run typecheck
            npx vitest run --reporter=default --reporter=junit --outputFile.junit="$REPORTS/mcp-server.xml"
            npm run build
          '''
        }
      }
    }

    stage('Dashboard') {
      steps {
        dir('dashboard') {
          sh '''
            npm ci --no-audit --no-fund
            npx eslint .
            npx vitest run --reporter=default --reporter=junit --outputFile.junit="$REPORTS/dashboard.xml"
            npm run build
          '''
        }
      }
    }

    stage('Explainer (Java)') {
      steps {
        dir('explainer-service') {
          sh 'mvn -B -ntp verify'
        }
      }
    }

    stage('Kubernetes manifests') {
      steps {
        sh '''
          kubeconform -strict -summary -kubernetes-version 1.31.0 \
            k8s/namespace.yaml k8s/secret.yaml k8s/postgres.yaml \
            k8s/seed-job.yaml k8s/rules-engine.yaml k8s/dashboard.yaml
        '''
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true,
            testResults: 'reports/*.xml, explainer-service/target/surefire-reports/*.xml'
    }
    success {
      echo 'All checks passed.'
    }
  }
}
