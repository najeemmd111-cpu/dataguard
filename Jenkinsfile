// Phase 5: the same pipeline as .github/workflows/ci.yml, run by a local Jenkins in Docker.
// Start Jenkins:  docker run -d -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock jenkins/jenkins:lts
// (install the Docker Pipeline plugin, then create a Pipeline job pointing at this repo)

pipeline {
  agent any
  environment {
    TEST_DATABASE_URL = 'postgresql://dataguard:dataguard@localhost:5432/dataguard'
  }
  stages {
    stage('Start Postgres') {
      steps {
        sh 'docker compose up -d postgres --wait'
      }
    }
    stage('Rules engine') {
      agent { docker { image 'python:3.12'; args '--network host'; reuseNode true } }
      steps {
        dir('rules-engine') {
          sh 'pip install -r requirements-dev.txt -r ../db/requirements.txt'
          sh 'ruff check .'
          sh 'pytest -v --junitxml=report.xml'
        }
      }
      post { always { junit 'rules-engine/report.xml' } }
    }
    stage('MCP server') {
      agent { docker { image 'node:22'; reuseNode true } }
      steps {
        dir('mcp-server') {
          sh 'npm ci && npm run typecheck && npm test && npm run build'
        }
      }
    }
    // stage('Playwright') { ... add in phase 5, publish e2e/playwright-report with publishHTML }
  }
  post {
    always { sh 'docker compose down -v || true' }
  }
}
