# 🚀 AI Agent Platform - Quick Start Guide

## Fixed Setup Instructions

The platform is now working! Follow these steps to get started:

### 1. Install Dependencies
```bash
# Install all required packages
python3 setup_platform.py
```

### 2. Configure API Keys
```bash
# Edit your .env file (created automatically by setup)
nano .env

# Add your API keys:
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # optional
```

### 3. Start the Platform
```bash
# Start the AI Agent hosting platform
python3 run_server.py --host 127.0.0.1 --port 8000
```

### 4. Access the Dashboard
Open your browser and go to:
```
http://127.0.0.1:8000/api/dashboard/ui
```

## 🎯 What You Can Do Now

### Web Dashboard Features
- ✅ **View Agent Overview**: See all running agents and their status
- ✅ **Create Agents**: Use the form to create different agent types
- ✅ **Monitor Metrics**: Real-time performance statistics
- ✅ **Control Agents**: Start, stop, and delete agents
- ✅ **Chat Interface**: Test agents directly from the dashboard

### Agent Types Available
1. **Conversational**: Chat-based agents for dialogue
2. **Reactive**: Tool-using agents that can calculate, search, etc.
3. **Planner**: Agents that break down complex tasks into plans

### API Endpoints
```bash
# List all agents
curl http://127.0.0.1:8000/api/agents/

# Create a new conversational agent
curl -X POST http://127.0.0.1:8000/api/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "conversational",
    "config": {
      "name": "MyBot",
      "model": "gpt-3.5-turbo",
      "temperature": 0.7
    },
    "name": "Test Agent"
  }'

# Chat with an agent (replace {agent_id} with actual ID)
curl -X POST http://127.0.0.1:8000/api/agents/{agent_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## 🧪 Test Examples

### Run Platform Demo
```bash
python3 examples/platform_demo.py
```

### Run Basic Examples
```bash
python3 examples/basic_usage.py
python3 examples/research_assistant.py
```

## 📊 Dashboard Overview

The dashboard shows:
- **Total Agents**: Number of created agents
- **Running Agents**: Currently active agents
- **Total Requests**: All processed requests
- **Success Rate**: Request success percentage

Each agent card displays:
- Agent name and status
- Configuration details
- Performance metrics
- Control buttons (Start/Stop/Delete/Chat)

## ✅ Troubleshooting

### Common Issues

1. **Import Errors**: Run `python3 setup_platform.py` again
2. **API Key Missing**: Edit `.env` file with your OpenAI key
3. **Port in Use**: Change port with `--port 8001`
4. **Dependencies**: Install with `pip3 install -r requirements.txt`

### Check Setup
```bash
python3 check_setup.py
```

## 🎉 Success!

Your AI Agent Platform is now ready for production use! You can:

- Host multiple AI agents simultaneously  
- Monitor their performance in real-time
- Create agents programmatically via REST API
- Scale horizontally with Docker deployment
- Integrate with external systems

The platform provides enterprise-grade agent hosting with web management interface! 🚀