### Data Capsule
Serverless Secure Data Room | AWS | Terraform

### Overview
Data Capsule is a serverless, cloud-native secure data room that provides time-limited, compute-mediated access to sensitive files.
Unlike traditional file sharing systems that expose downloadable links, Data Capsule prevents uncontrolled file possession by routing all interactions through backend compute. Files are stored privately and automatically deleted after expiry.
The infrastructure is fully provisioned using Terraform to ensure reproducibility and consistency across environments.

### Architecture
The system follows a serverless, event-driven design:
Frontend
•	Static web interface hosted on Amazon S3
API Layer
•	Amazon API Gateway (HTTP interface)
Compute
•	AWS Lambda (Python)
Storage
•	Amazon S3 (private bucket, encrypted at rest)
Metadata
•	Amazon DynamoDB (TTL-enabled lifecycle management)
Eventing
•	Amazon EventBridge (scheduled cleanup)
Notifications
•	Amazon SNS
Infrastructure
•	Terraform (Infrastructure as Code)

### Request Flow
1.	User uploads file via UI.
2.	API Gateway invokes Lambda.
3.	File stored in private S3 bucket.
4.	Metadata stored in DynamoDB with TTL attribute.
5.	Access to file is always mediated via Lambda.
6.	After TTL expiration, cleanup Lambda deletes associated objects.
No direct S3 object exposure is allowed.

### Key Engineering Decisions
•	Compute-Mediated Access
Prevents direct file downloads and enforces controlled interaction.
•	TTL-Based Lifecycle
DynamoDB TTL ensures automatic expiration without manual scheduling complexity.
•	Serverless Architecture
Eliminates server management and scales automatically based on demand.
•	Infrastructure as Code
Terraform ensures reproducible deployments and environment consistency.
•	Least Privilege IAM
Lambda roles restricted to minimal required permissions.

### Security Considerations
•	S3 Block Public Access enabled
•	Server-side encryption (AES-256)
•	No pre-signed download URLs
•	API Gateway as single entry point
•	Automated deletion of expired data

### Deployment
Requirements
•	AWS CLI configured
•	Terraform installed
Deploy
terraform init
terraform apply
Infrastructure provisioning includes:
•	S3 bucket
•	DynamoDB table
•	Lambda functions
•	API Gateway
•	EventBridge rules
•	IAM roles

### Scalability & Cost
•	Fully serverless → automatic scaling
•	Pay-per-use pricing model
•	Estimated cost under light usage: <$1/month
The system scales horizontally with Lambda concurrency and API Gateway throughput.

### Future Enhancements
•	Authentication via Amazon Cognito
•	CI/CD pipeline integration
•	CloudFront distribution
•	Advanced monitoring (CloudWatch dashboards)
•	KMS-managed encryption keys
•	Access analytics and auditing

### What This Project Demonstrates
•	Cloud-native architecture design
•	Multi-service AWS integration
•	Event-driven lifecycle management
•	Infrastructure as Code best practices
•	Secure data handling patterns
•	Cost-aware distributed system design
