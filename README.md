
pipeline {
  agent any

  environment {
    AWS_REGION     = 'us-east-1'
    AWS_ACCOUNT_ID = '502710547370'
    ECR_REPO       = 'hostel-management-1'
    IMAGE_TAG      = 'latest1'
    REGISTRY       = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    IMAGE          = "${REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"
    CLUSTER_NAME   = 'hostel-cluster-2'
    GIT_URL        = 'https://github.com/RohitGadhave2k3/2-tier-eks.git'
  }

  stages {

    stage('AWS Auth') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws_id']]) {
          sh 'aws sts get-caller-identity'
        }
      }
    }

    stage('Clone Git Repository') {
      steps {
        sh '''
          rm -rf workspace
          git clone ${GIT_URL} workspace
        '''
      }
    }

    stage('ECR Login & Ensure Repo') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws_id']]) {
          sh '''
            aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
              aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}"

            aws ecr get-login-password --region ${AWS_REGION} | \
              docker login --username AWS --password-stdin ${REGISTRY}
          '''
        }
      }
    }

    stage('Build & Push Image') {
      steps {
        sh '''
          cd workspace
          docker build -t ${ECR_REPO}:${IMAGE_TAG} .
          docker tag  ${ECR_REPO}:${IMAGE_TAG} ${IMAGE}
          docker push ${IMAGE}
        '''
      }
    }

    stage('Create EKS Cluster') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws_id']]) {
          sh '''
            eksctl get cluster --region ${AWS_REGION} | grep -w ${CLUSTER_NAME} || \
            eksctl create cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --nodes 2 --node-type t3.medium
          '''
        }
      }
    }

    stage('Deploy to EKS') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws_id']]) {
          sh '''
            aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}
            cd workspace/k8s

            kubectl apply -f mariadb.yml
            kubectl apply -f deployment.yml

            kubectl set image deployment/hostel-management hostel-management=${IMAGE} --record

            kubectl apply -f service.yml

            kubectl rollout status deployment/hostel-management --timeout=5m
          '''
        }
      }
    }

    stage('Show LB URL') {
      steps {
        sh '''
          aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}
          echo "LoadBalancer URL:"
          kubectl get svc hostel-management-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'; echo
        '''
      }
    }
  }

  post {
    success {
      echo "Deployment complete. Image: ${IMAGE}"
    }
    failure {
      echo "Pipeline failed — check stage logs."
    }
  }
}

##############################################################################################################################################################################################################
[ec2-user@ip-172-31-65-206 ~]$ aws eks update-kubeconfig --region us-east-1 --name hostel-cluster-2
Added new context arn:aws:eks:us-east-1:502710547370:cluster/hostel-cluster-2 to /home/ec2-user/.kube/config
[ec2-user@ip-172-31-65-206 ~]$ eksctl get cluster --region us-east-1
NAME                    REGION          EKSCTL CREATED
hostel-cluster-2        us-east-1       True
[ec2-user@ip-172-31-65-206 ~]$

docker build -t hostel-management:latest1 .
docker tag hostel-management:latest1 502710547370.dkr.ecr.us-east-1.amazonaws.com/hostel-management-1:latest1
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 502710547370.dkr.ecr.us-east-1.amazonaws.com
docker push 502710547370.dkr.ecr.us-east-1.amazonaws.com/hostel-management-1:latest1
kubectl set image deployment/hostel-management hostel-management=502710547370.dkr.ecr.us-east-1.amazonaws.com/hostel-management-1:latest1
kubectl rollout status deployment/hostel-management
