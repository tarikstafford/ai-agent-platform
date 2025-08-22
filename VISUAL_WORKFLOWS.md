# 🎨 Visual Workflow Builder Integration

The AI Agent Platform now includes **Langflow** integration for visual agent creation with drag-and-drop workflow building!

## ✨ New Features

### Visual Workflow Builder
- **Drag-and-Drop Interface**: Create complex agent workflows visually
- **Pre-built Components**: LLMs, tools, memory, and I/O components
- **Workflow Templates**: Ready-made templates for common use cases
- **Real-time Testing**: Test workflows with sample inputs
- **Export/Import**: Save and share workflow definitions

### LangflowAgent Type
- **Visual Workflow Execution**: Run workflows created in the visual builder
- **Seamless Integration**: Works with existing agent management system
- **Full API Support**: Create, manage, and interact via REST API
- **Dashboard Integration**: Visual builder embedded in dashboard

## 🚀 Quick Start

### 1. Install Langflow
```bash
# Install Langflow dependencies
pip install langflow uvicorn fastapi

# Or update requirements
python setup_platform.py
```

### 2. Access Visual Builder
1. Start the platform: `python run_server.py`
2. Open dashboard: `http://127.0.0.1:8000/api/dashboard/ui`
3. Select "Visual Workflow" agent type
4. Click "🎨 Open Visual Builder"

### 3. Create Your First Visual Workflow
1. Choose a template or start blank
2. Drag components onto the canvas
3. Connect components with edges
4. Configure component settings
5. Test with sample inputs
6. Save and create agent

## 🧩 Available Components

### Input/Output
- **TextInput**: Accept text from users
- **FileInput**: Handle file uploads  
- **TextOutput**: Return text responses
- **FileOutput**: Generate file downloads

### Language Models
- **OpenAI**: GPT-3.5, GPT-4 models
- **Anthropic**: Claude models
- **Local Models**: Ollama, HuggingFace

### Tools
- **Calculator**: Mathematical operations
- **WebSearch**: Search the internet
- **APICall**: Make HTTP requests
- **FileOperations**: Read/write files

### Memory
- **ConversationBuffer**: Store chat history
- **VectorStore**: Semantic search
- **EntityMemory**: Track entities

### Logic
- **Conditional**: If/then/else logic
- **Loop**: Iterate over data
- **Transform**: Data manipulation

## 📋 Workflow Templates

### 1. Simple Chat Agent
Basic conversational AI with OpenAI
- **Use Case**: Customer support, general chat
- **Components**: TextInput → OpenAI → TextOutput

### 2. RAG Knowledge Agent  
Retrieval-augmented generation with vector search
- **Use Case**: Knowledge base, document Q&A
- **Components**: Query → VectorSearch → Context + LLM → Answer

### 3. Tool-Using Agent
Agent with calculator and web search capabilities
- **Use Case**: Research, calculations, multi-step tasks
- **Components**: Input → Agent → Tools → Output

### 4. Multi-Step Planner
Break down complex tasks into steps
- **Use Case**: Project planning, complex workflows
- **Components**: Goal → Planner → Executor → Results

## 🔧 API Endpoints

### Langflow Management
```bash
# Check Langflow status
GET /api/langflow/status

# Initialize Langflow server
POST /api/langflow/initialize

# List workflows
GET /api/langflow/workflows

# Create workflow
POST /api/langflow/workflows
{
  "name": "My Workflow",
  "description": "Custom workflow",
  "template": "simple_chat"
}

# Get workflow details
GET /api/langflow/workflows/{flow_id}

# Test workflow
POST /api/langflow/workflows/{flow_id}/test
{
  "inputs": {"input": "test message"}
}

# Export workflow
GET /api/langflow/workflows/{flow_id}/export
```

### Agent Creation
```bash
# Create agent from visual workflow
POST /api/langflow/agents
{
  "name": "My Visual Agent",
  "flow_id": "workflow-uuid-here",
  "description": "Agent from visual workflow"
}
```

## 💻 Code Examples

### Creating Visual Workflow Agent
```python
from langflow_integration import LangflowAgent, WorkflowBuilder
from agents import AgentConfig

# Initialize builder
builder = WorkflowBuilder()
await builder.initialize()

# Create workflow from template
flow_id = builder.create_from_template("simple_chat", "my_agent")

# Create agent
config = AgentConfig(name="VisualAgent", model="langflow-workflow")
agent = LangflowAgent(config, flow_id=flow_id)

# Use agent
response = await agent.run("Hello!")
print(response.content)
```

### Custom Workflow Definition
```python
# Define workflow structure
workflow_data = {
    "name": "Custom Workflow",
    "nodes": [
        {"id": "input", "type": "TextInput"},
        {"id": "llm", "type": "OpenAI", "config": {"model": "gpt-4"}},
        {"id": "output", "type": "TextOutput"}
    ],
    "edges": [
        {"source": "input", "target": "llm"},
        {"source": "llm", "target": "output"}
    ]
}

# Create workflow
flow_id = builder.langflow_server.create_flow(workflow_data)
```

## 🎯 Use Cases

### 1. Customer Support Bot
- **Template**: Simple Chat Agent
- **Features**: Natural conversation, context awareness
- **Integration**: Knowledge base, ticketing system

### 2. Document Analysis Assistant
- **Template**: RAG Knowledge Agent  
- **Features**: Document upload, semantic search, Q&A
- **Integration**: Vector database, file storage

### 3. Research Agent
- **Template**: Tool-Using Agent
- **Features**: Web search, calculation, synthesis
- **Integration**: Search APIs, data sources

### 4. Content Generation Pipeline
- **Custom Workflow**: Multi-step content creation
- **Features**: Research → Outline → Writing → Review
- **Integration**: CMS, publishing tools

## 🔄 Workflow Management

### Lifecycle
1. **Design**: Visual drag-and-drop creation
2. **Test**: Validate with sample inputs
3. **Deploy**: Create agent from workflow
4. **Monitor**: Track performance in dashboard
5. **Iterate**: Modify and redeploy

### Best Practices
- **Start Simple**: Begin with templates, then customize
- **Test Thoroughly**: Use various input scenarios
- **Version Control**: Export workflows for backup
- **Monitor Performance**: Track agent metrics
- **Iterate Quickly**: Visual interface enables rapid changes

## 🛠️ Advanced Features

### Custom Components
Create reusable components for your workflows:
```python
from langflow_integration import BaseComponent

class CustomTool(BaseComponent):
    def execute(self, input_data):
        # Your custom logic
        return processed_result
```

### Workflow Validation
```python
validation = builder.validate_workflow(workflow_data)
if validation["valid"]:
    print("Workflow is valid!")
else:
    print("Errors:", validation["errors"])
```

### Batch Processing
```python
# Process multiple inputs
inputs = [{"input": msg} for msg in messages]
results = await agent.batch_process(inputs)
```

## 🤝 Integration Points

### Dashboard Integration
- Visual builder embedded in dashboard
- Seamless agent creation workflow  
- Real-time status updates
- Performance monitoring

### API Integration
- RESTful endpoints for all operations
- WebSocket for real-time updates
- Standard agent interface
- Export/import capabilities

### Platform Integration
- Works with existing agent types
- Shared hosting infrastructure
- Common management interface
- Unified monitoring and metrics

## 🎉 Benefits

### For Developers
- **Rapid Prototyping**: Quickly test ideas visually
- **No Code Required**: Build complex workflows without coding
- **Easy Debugging**: Visual flow makes issues obvious
- **Reusable Components**: Build once, use everywhere

### For Non-Technical Users
- **Intuitive Interface**: Drag-and-drop simplicity
- **Immediate Feedback**: Test workflows instantly
- **Template Library**: Start with proven patterns
- **Visual Understanding**: See how workflows operate

### For Teams
- **Collaborative Design**: Share and iterate on workflows
- **Consistent Patterns**: Standardized approach across team
- **Knowledge Sharing**: Visual workflows are self-documenting
- **Rapid Deployment**: From idea to production quickly

## 🔮 Future Enhancements

- **More Templates**: Additional workflow patterns
- **Custom Components**: User-defined reusable components  
- **Workflow Marketplace**: Share and discover workflows
- **Advanced Debugging**: Step-through execution
- **A/B Testing**: Compare workflow variations
- **Analytics Integration**: Detailed performance insights

---

**Start building visual workflows today!** 🚀

Access the visual builder at: `http://127.0.0.1:8000/api/dashboard/builder`