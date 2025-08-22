# Deployment Guide

This guide covers different deployment options for the AI Agent Platform.

## Local Development

### Quick Start
```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
python run_server.py --host 127.0.0.1 --port 8000

# Access dashboard
open http://127.0.0.1:8000/api/dashboard/ui
```

## Docker Deployment

### Build and Run
```bash
# Build the image
docker build -t ai-agent-platform .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/data:/app/data \
  ai-agent-platform
```

### Using Docker Compose
```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start the platform
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the platform
docker-compose down
```

## Production Deployment

### Environment Variables
Required:
- `OPENAI_API_KEY` - Your OpenAI API key
- `ANTHROPIC_API_KEY` - Your Anthropic API key (optional)

Optional:
- `DEFAULT_MODEL` - Default LLM model (default: gpt-3.5-turbo)
- `DEFAULT_TEMPERATURE` - Default temperature (default: 0.7)
- `LOG_LEVEL` - Logging level (default: INFO)
- `AGENT_MAX_ITERATIONS` - Max iterations per agent (default: 10)
- `MEMORY_PERSIST_DIRECTORY` - Directory for persistent memory

### Security Considerations

1. **API Keys**: Store API keys securely using environment variables or secrets management
2. **Network**: Use HTTPS in production with proper SSL certificates
3. **Authentication**: Add authentication for the dashboard and API endpoints
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **Monitoring**: Set up logging and monitoring for production usage

### Scaling

#### Horizontal Scaling
The platform can be scaled horizontally by:
1. Running multiple instances behind a load balancer
2. Using a shared database for agent state (Redis/PostgreSQL)
3. Implementing distributed agent registry

#### Vertical Scaling
- Increase memory and CPU for handling more concurrent agents
- Optimize agent configurations (temperature, max_tokens)
- Use faster storage for agent persistence

### Monitoring

#### Health Checks
- `/health` - Basic health check endpoint
- Monitor agent status via `/api/dashboard/stats`
- WebSocket connections for real-time monitoring

#### Logging
The platform uses structured logging with:
- Request/response logging
- Agent execution logs
- Error tracking and alerts

#### Metrics
Available metrics:
- Total agents
- Active/running agents
- Request count and success rate
- Average response times
- Agent-specific metrics

## Cloud Deployment

### AWS Deployment
```bash
# Using ECS or EKS
# 1. Push image to ECR
# 2. Create ECS service or Kubernetes deployment
# 3. Configure load balancer and security groups
# 4. Set up secrets for API keys
```

### Google Cloud Platform
```bash
# Using Cloud Run
gcloud run deploy ai-agent-platform \
  --image gcr.io/PROJECT-ID/ai-agent-platform \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Container Instances
```bash
# Deploy to Azure
az container create \
  --resource-group myResourceGroup \
  --name ai-agent-platform \
  --image ai-agent-platform \
  --ports 8000
```

## Backup and Recovery

### Data Backup
```bash
# Backup agent configurations
tar -czf agent-configs-backup.tar.gz agent_configs/

# Backup agent data and logs
tar -czf agent-data-backup.tar.gz data/ logs/
```

### Recovery
```bash
# Restore configurations
tar -xzf agent-configs-backup.tar.gz

# Restart platform to load saved agents
docker-compose restart
```

## Troubleshooting

### Common Issues

1. **Agents not starting**: Check API keys and model availability
2. **Memory issues**: Increase container memory limits
3. **Performance**: Monitor agent metrics and optimize configurations
4. **Connectivity**: Check network configuration and firewall rules

### Debug Mode
```bash
python run_server.py --debug --host 127.0.0.1 --port 8000
```

### Logs Location
- Application logs: `logs/agent.log`
- Agent configurations: `agent_configs/`
- Agent data: `data/`