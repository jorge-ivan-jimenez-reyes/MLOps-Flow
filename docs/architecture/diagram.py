from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EKS
from diagrams.aws.storage import S3
from diagrams.aws.database import RDS
from diagrams.aws.network import VPC, NATGateway, InternetGateway, ELB
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.mlops import Mlflow
from diagrams.k8s.compute import Pod
from diagrams.onprem.client import User

# Estilo visual limpio
graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "pad": "0.5",
    "rankdir": "LR",
    "nodesep": "1.0",
    "ranksep": "2.0",
}

filename = "docs/architecture/images/mlops_architecture"

with Diagram("FHIR Automapper - AWS Infrastructure", show=False, graph_attr=graph_attr, filename=filename, direction="LR"):
    
    user = User("User")

    with Cluster("AWS (us-east-1)"):
        
        igw = InternetGateway("IGW")
        nat = NATGateway("NAT")
        elb = ELB("ALB")
        
        with Cluster("VPC 10.0.0.0/16"):
            
            with Cluster("EKS Cluster (K8s 1.29)\n2x t3.medium nodes"):
                
                frontend = Pod("Frontend")
                gateway = Pod("Gateway API")
                inference = Pod("Inference")
                trainer = Pod("Trainer")
                mlflow_pod = Mlflow("MLflow")
                prom = Prometheus("Prometheus")
                grafana = Grafana("Grafana")
            
            rds = RDS("Postgres 15\ndb.t3.micro")
        
        s3 = S3("S3 Bucket\nMLflow Artifacts")

    # User flow
    user >> igw >> elb >> frontend >> gateway >> inference
    
    # MLOps flow
    trainer >> mlflow_pod >> s3
    mlflow_pod >> rds
    inference - Edge(style="dashed") - s3
    
    # Monitoring
    prom - Edge(style="dotted") - [gateway, inference]
    grafana >> prom
