# CAIseiro - AI-Powered Poultry Farm Monitoring System

**Team**: AI Rebels  
**Product**: CAIseiro (Caseiro + AI)  
**AI Model**: Caseiro 2o

## Brief Description

CAIseiro is an intelligent early-warning system that uses IoT sensors and AI to detect thermal stress in poultry farms before it impacts chicken health and farm productivity. The system monitors environmental conditions and equipment performance, providing real-time alerts and preventive recommendations to farm operators (caseiros) through AI-powered analysis using our custom Caseiro 2o model.

## Problem Statement

Thermal stress is a critical issue in poultry farming that significantly impacts both animal welfare and farm economics:

### Impact on Chickens
- **Heat stress**: Chickens drink excessively and lose weight, affecting growth patterns
- **Cold stress**: Chickens clump together for warmth, potentially causing deaths from trampling or suffocation
- **Growth irregularities**: Unpredictable development patterns disrupt stock management and logistics

### Economic Consequences
- **Processing challenges**: Unexpectedly heavy chickens require more manual processing steps at slaughterhouses (matadouros)
- **Restaurant operations**: Oversized chickens don't fit standard grilling equipment at churrasqueiras, reducing capacity and increasing cooking times
- **Supply chain disruption**: Inconsistent chicken sizes complicate inventory management and delivery schedules

### Current Infrastructure Limitations
- **Equipment reliability**: Ventilation systems and boilers frequently fail and require maintenance
- **Detection delays**: Farm operators (caseiros) typically only detect equipment failures after they occur
- **Maintenance bottlenecks**: Mechanics and replacement parts can take days to arrive, during which thermal stress continues to affect livestock
- **AWS quota constraints**: Limited by AWS quotas, particularly for phone provider services affecting SMS notification capacity

## Proposed Solution

### Intelligent Monitoring System
Our solution combines IoT sensor networks with AI-powered analysis to provide early detection of thermal stress conditions:

#### Sensor Network
- **Environmental monitoring**: Temperature, humidity, and ammonia concentration sensors
- **Equipment monitoring**: Current variations, frequency analysis, and fan velocity sensors
- **Real-time data collection**: Continuous monitoring of critical parameters

#### AI-Powered Analysis with Caseiro 2o
- **Custom AI Agent**: Caseiro 2o model "judges" events and makes intelligent decisions on whether to notify
- **RAG (Retrieval-Augmented Generation)**: Leverages AWS Knowledge Base with poultry farming best practices
- **AWS-hosted knowledge base**: Contains educational data and worldwide guidelines for optimal poultry farm management
- **Expandable database**: Supports integration of equipment manuals and mechanic documentation

#### Automated Decision & Notification System
1. **Data ingestion**: Sensor data from vents and boilers is automatically published to AWS S3
2. **Intelligent processing**: S3 triggers AWS Lambda functions when new objects are detected
3. **AI decision-making**: Caseiro 2o AI Agent analyzes data using Action Groups and decides whether intervention is needed
4. **Smart notifications**: SMS alerts sent via AWS SNS directly to caseiros or technicians
5. **Actionable recommendations**: When alerts are sent, they include specific preventive measures to prevent equipment malfunction

### Key Benefits
- **Proactive intervention**: Detect potential issues before they impact animal welfare
- **Reduced losses**: Minimize chicken mortality and weight loss due to thermal stress
- **Improved productivity**: Maintain consistent growth patterns for better stock management
- **Cost savings**: Reduce emergency maintenance calls and optimize equipment usage
- **Enhanced animal welfare**: Ensure optimal living conditions for poultry

## Architecture Overview

```
[IoT Sensors (Vents/Boilers)] → [AWS S3] → [Lambda Trigger] → [Caseiro 2o AI Agent + RAG] → [Decision Engine] → [AWS SNS] → [SMS Notifications]
```

## Technology Stack
- **Primary Language**: Python
- **Cloud Platform**: Amazon Web Services (AWS)
- **Data Storage**: AWS S3 buckets
- **Serverless Computing**: AWS Lambda (triggered by S3 new object events)
- **AI/ML**: Caseiro 2o AI Agent with Retrieval-Augmented Generation (RAG)
- **Knowledge Management**: AWS Knowledge Base
- **Action Processing**: Lambda Action Groups for AI Agent
- **Notification Service**: AWS SNS (SMS notifications)
- **IoT Sensors**: Temperature, humidity, ammonia, current, frequency, and velocity sensors for vents and boilers
- **Frontend**: Web application for data visualization and monitoring dashboard

## Target Users
- **Primary**: Farm operators (caseiros) in Portuguese poultry farms
- **Secondary**: Farm owners, veterinarians, and maintenance teams
- **Beneficiaries**: Downstream supply chain including processing plants and restaurants

---

**AI Rebels Team Project**  
*This project was developed for Geekathon with the goal of improving animal welfare and farm efficiency through intelligent monitoring and early intervention systems powered by our custom Caseiro 2o AI model.*
