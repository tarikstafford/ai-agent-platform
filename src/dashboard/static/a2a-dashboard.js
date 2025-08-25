/**
 * A2A Communication Dashboard JavaScript
 * 
 * This file provides the interactive functionality for the A2A dashboard,
 * including network visualization, real-time updates, and agent management.
 */

class A2ADashboard {
    constructor() {
        this.networkData = null;
        this.networkSvg = null;
        this.simulation = null;
        this.agents = [];
        this.selectedAgent = null;
        this.messageLog = [];
        this.autoScroll = true;
        
        // WebSocket for real-time updates
        this.socket = null;
        
        // Update intervals
        this.updateInterval = null;
        this.statsInterval = null;
        
        this.init();
    }
    
    async init() {
        this.initializeWebSocket();
        this.initializeNetwork();
        this.startPeriodicUpdates();
        await this.loadInitialData();
        this.populateAgentSelects();
    }
    
    initializeWebSocket() {
        // Initialize WebSocket connection for real-time updates
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/socket.io/`;
        
        // Note: This would require Socket.IO setup
        // For now, we'll use polling
        console.log('WebSocket connection would be established to:', wsUrl);
    }
    
    initializeNetwork() {
        const svg = d3.select("#network-graph");
        const width = svg.node().getBoundingClientRect().width;
        const height = 500;
        
        this.networkSvg = svg
            .attr("width", width)
            .attr("height", height);
        
        // Initialize force simulation
        this.simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadNetworkOverview(),
                this.loadActiveTasks(),
                this.loadActiveCollaborations(),
                this.updateStats()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.addMessageToLog('Error loading initial data: ' + error.message, 'error');
        }
    }
    
    async loadNetworkOverview() {
        try {
            const response = await fetch('/api/a2a/network/overview');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.networkData = data.network_data;
            this.agents = data.network_data.agents;
            
            this.renderNetwork();
            this.addMessageToLog(`Network overview loaded: ${this.agents.length} agents`);
            
        } catch (error) {
            console.error('Error loading network overview:', error);
            this.addMessageToLog('Error loading network overview: ' + error.message, 'error');
        }
    }
    
    async loadActiveTasks() {
        try {
            const response = await fetch('/api/a2a/tasks/active');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.renderActiveTasks(data.active_tasks || []);
            
        } catch (error) {
            console.error('Error loading active tasks:', error);
            this.addMessageToLog('Error loading active tasks: ' + error.message, 'error');
        }
    }
    
    async loadActiveCollaborations() {
        try {
            const response = await fetch('/api/a2a/collaborations/active');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.renderActiveCollaborations(data.active_collaborations || []);
            
        } catch (error) {
            console.error('Error loading active collaborations:', error);
            this.addMessageToLog('Error loading active collaborations: ' + error.message, 'error');
        }
    }
    
    async updateStats() {
        try {
            // Update overall statistics
            document.getElementById('active-agents-count').textContent = this.agents.length;
            
            // Count active tasks and collaborations
            const activeTasks = document.querySelectorAll('.task-item').length;
            const activeCollabs = document.querySelectorAll('.collaboration-item').length;
            
            document.getElementById('active-tasks-count').textContent = activeTasks;
            document.getElementById('collaborations-count').textContent = activeCollabs;
            
            // Calculate message rate (mock data for now)
            const messageRate = Math.floor(Math.random() * 50) + 10;
            document.getElementById('message-rate').textContent = messageRate;
            
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }
    
    renderNetwork() {
        if (!this.networkData) return;
        
        const svg = this.networkSvg;
        const width = svg.node().getBoundingClientRect().width;
        const height = 500;
        
        // Clear existing elements
        svg.selectAll("*").remove();
        
        // Create links
        const links = this.networkData.connections.map(d => ({
            source: d.source,
            target: d.target,
            lastSeen: d.last_seen
        }));
        
        // Create nodes
        const nodes = this.agents.map(agent => ({
            id: agent.id,
            name: agent.name,
            status: agent.status,
            capabilities: agent.capabilities,
            load: agent.load || 0
        }));
        
        // Update simulation
        this.simulation
            .nodes(nodes)
            .force("link").links(links);
        
        // Add links
        const link = svg.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(links)
            .enter().append("line")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 2);
        
        // Add nodes
        const node = svg.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .attr("class", "agent-node")
            .call(d3.drag()
                .on("start", this.dragStarted.bind(this))
                .on("drag", this.dragged.bind(this))
                .on("end", this.dragEnded.bind(this)));
        
        // Add circles for agents
        node.append("circle")
            .attr("r", d => 10 + (d.capabilities.length * 2))
            .attr("fill", d => this.getAgentColor(d.status))
            .attr("stroke", "#fff")
            .attr("stroke-width", 2);
        
        // Add labels
        node.append("text")
            .attr("dy", -15)
            .attr("text-anchor", "middle")
            .style("font-size", "10px")
            .style("font-weight", "bold")
            .text(d => d.name);
        
        // Add load indicator
        node.append("circle")
            .attr("r", d => 3 + (d.load * 5))
            .attr("cx", 8)
            .attr("cy", -8)
            .attr("fill", d => d.load > 0.7 ? "#dc3545" : d.load > 0.4 ? "#ffc107" : "#28a745")
            .attr("opacity", 0.8);
        
        // Add click handler
        node.on("click", (event, d) => {
            this.selectAgent(d);
        });
        
        // Update positions on simulation tick
        this.simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        // Restart simulation
        this.simulation.alpha(1).restart();
    }
    
    getAgentColor(status) {
        const colors = {
            'running': '#28a745',
            'idle': '#17a2b8',
            'busy': '#ffc107',
            'error': '#dc3545',
            'stopped': '#6c757d'
        };
        return colors[status] || '#6c757d';
    }
    
    selectAgent(agent) {
        this.selectedAgent = agent;
        this.renderAgentDetails(agent);
        
        // Highlight selected agent
        this.networkSvg.selectAll(".agent-node circle")
            .attr("stroke-width", d => d.id === agent.id ? 4 : 2)
            .attr("stroke", d => d.id === agent.id ? "#007bff" : "#fff");
    }
    
    async renderAgentDetails(agent) {
        const detailsContainer = document.getElementById('agent-details');
        
        try {
            // Fetch detailed agent stats
            const response = await fetch(`/api/a2a/agents/${agent.id}/stats`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            const stats = data.stats || {};
            
            detailsContainer.innerHTML = `
                <h6 class="fw-bold text-primary">${agent.name}</h6>
                <p class="text-muted small">ID: ${agent.id}</p>
                
                <div class="mb-3">
                    <span class="badge bg-${this.getStatusBadgeClass(agent.status)}">${agent.status}</span>
                    <span class="badge bg-secondary ms-1">Load: ${Math.round(agent.load * 100)}%</span>
                </div>
                
                <h6 class="fw-bold">Capabilities</h6>
                <div class="mb-3">
                    ${agent.capabilities.map(cap => 
                        `<span class="capability-tag">${cap}</span>`
                    ).join('')}
                </div>
                
                <h6 class="fw-bold">Communication Stats</h6>
                <ul class="list-unstyled small">
                    <li>Messages Sent: ${stats.communication?.messages_sent || 0}</li>
                    <li>Messages Received: ${stats.communication?.messages_received || 0}</li>
                    <li>Known Agents: ${stats.communication?.known_agents || 0}</li>
                </ul>
                
                <h6 class="fw-bold">Task Stats</h6>
                <ul class="list-unstyled small">
                    <li>Active Tasks: ${stats.tasks?.active_tasks || 0}</li>
                    <li>Success Rate: ${Math.round((stats.tasks?.success_rate || 0) * 100)}%</li>
                </ul>
                
                <div class="mt-3">
                    <button class="btn btn-sm btn-primary" onclick="dashboard.pingAgent('${agent.id}')">
                        <i class="fas fa-satellite-dish"></i> Ping
                    </button>
                    <button class="btn btn-sm btn-outline-primary ms-1" onclick="dashboard.showAgentTasks('${agent.id}')">
                        <i class="fas fa-tasks"></i> Tasks
                    </button>
                </div>
            `;
            
        } catch (error) {
            detailsContainer.innerHTML = `
                <h6 class="fw-bold text-primary">${agent.name}</h6>
                <p class="text-danger">Error loading agent details: ${error.message}</p>
            `;
        }
    }
    
    getStatusBadgeClass(status) {
        const classes = {
            'running': 'success',
            'idle': 'info',
            'busy': 'warning',
            'error': 'danger',
            'stopped': 'secondary'
        };
        return classes[status] || 'secondary';
    }
    
    renderActiveTasks(tasks) {
        const container = document.getElementById('active-tasks-list');
        
        if (tasks.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No active tasks</p>';
            return;
        }
        
        container.innerHTML = tasks.map(task => `
            <div class="task-item d-flex justify-content-between align-items-center p-2 mb-2 border rounded">
                <div>
                    <div class="fw-bold">${task.type}</div>
                    <div class="small text-muted">${task.description || 'No description'}</div>
                    <div class="small">
                        Requester: <span class="text-primary">${task.requester}</span>
                        ${task.assigned_to ? `→ <span class="text-success">${task.assigned_to}</span>` : ''}
                    </div>
                </div>
                <div class="text-end">
                    <span class="badge task-status-badge bg-${this.getTaskStatusClass(task.status)}">
                        ${task.status}
                    </span>
                    <div class="small text-muted">
                        Progress: ${Math.round(task.progress * 100)}%
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    getTaskStatusClass(status) {
        const classes = {
            'pending': 'secondary',
            'assigned': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning'
        };
        return classes[status] || 'secondary';
    }
    
    renderActiveCollaborations(collaborations) {
        const container = document.getElementById('collaborations-list');
        
        if (collaborations.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No active collaborations</p>';
            return;
        }
        
        container.innerHTML = collaborations.map(collab => `
            <div class="collaboration-item collaboration-card p-3 mb-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="fw-bold mb-0">${collab.title}</h6>
                    <span class="badge bg-${this.getCollabStatusClass(collab.status)}">${collab.status}</span>
                </div>
                <p class="text-muted small mb-2">${collab.description}</p>
                <div class="small">
                    <div><strong>Coordinator:</strong> ${collab.coordinator}</div>
                    <div><strong>Participants:</strong> ${collab.participants.join(', ')}</div>
                    <div class="text-muted">Created: ${new Date(collab.created_at).toLocaleString()}</div>
                </div>
            </div>
        `).join('');
    }
    
    getCollabStatusClass(status) {
        const classes = {
            'forming': 'warning',
            'active': 'success',
            'completing': 'info',
            'completed': 'primary',
            'failed': 'danger',
            'cancelled': 'secondary'
        };
        return classes[status] || 'secondary';
    }
    
    addMessageToLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const messageObj = { message, type, timestamp };
        
        this.messageLog.push(messageObj);
        
        // Keep only last 100 messages
        if (this.messageLog.length > 100) {
            this.messageLog.shift();
        }
        
        const logContainer = document.getElementById('message-log');
        const messageElement = document.createElement('div');
        messageElement.className = `message-item ${type}`;
        messageElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <span>${message}</span>
                <small class="text-muted">${timestamp}</small>
            </div>
        `;
        
        logContainer.appendChild(messageElement);
        
        if (this.autoScroll) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    
    async populateAgentSelects() {
        const selects = ['requester-agent', 'coordinator-agent'];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            select.innerHTML = '<option value="">Select agent...</option>';
            
            this.agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = `${agent.name} (${agent.status})`;
                select.appendChild(option);
            });
        });
        
        // Populate participant checkboxes
        const participantContainer = document.getElementById('participant-checkboxes');
        participantContainer.innerHTML = '';
        
        this.agents.forEach(agent => {
            const div = document.createElement('div');
            div.className = 'form-check';
            div.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${agent.id}" id="participant-${agent.id}">
                <label class="form-check-label" for="participant-${agent.id}">
                    ${agent.name} <small class="text-muted">(${agent.capabilities.join(', ')})</small>
                </label>
            `;
            participantContainer.appendChild(div);
        });
    }
    
    // Event handlers
    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    async pingAgent(agentId) {
        if (!this.selectedAgent) return;
        
        try {
            const response = await fetch(`/api/a2a/agents/${agentId}/ping`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender_id: this.selectedAgent.id,
                    timeout: 10
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.addMessageToLog(`Ping successful: ${this.selectedAgent.name} → ${agentId}`, 'success');
            } else {
                this.addMessageToLog(`Ping failed: ${this.selectedAgent.name} → ${agentId}`, 'error');
            }
            
        } catch (error) {
            this.addMessageToLog(`Ping error: ${error.message}`, 'error');
        }
    }
    
    startPeriodicUpdates() {
        // Update data every 30 seconds
        this.updateInterval = setInterval(() => {
            this.loadNetworkOverview();
            this.loadActiveTasks();
            this.loadActiveCollaborations();
        }, 30000);
        
        // Update stats every 5 seconds
        this.statsInterval = setInterval(() => {
            this.updateStats();
        }, 5000);
    }
    
    stopPeriodicUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
    }
    
    cleanup() {
        this.stopPeriodicUpdates();
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Global dashboard instance
let dashboard;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new A2ADashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (dashboard) {
        dashboard.cleanup();
    }
});

// Global functions for UI interactions
async function refreshNetwork() {
    await dashboard.loadNetworkOverview();
    dashboard.addMessageToLog('Network data refreshed');
}

function toggleLayout() {
    if (dashboard.simulation) {
        dashboard.simulation.alpha(1).restart();
    }
}

function clearMessageLog() {
    document.getElementById('message-log').innerHTML = '<p class="text-muted">Message log cleared...</p>';
    dashboard.messageLog = [];
}

function toggleAutoScroll() {
    dashboard.autoScroll = !dashboard.autoScroll;
    const button = event.target.closest('button');
    const icon = button.querySelector('i');
    
    if (dashboard.autoScroll) {
        icon.className = 'fas fa-arrow-down';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-primary');
    } else {
        icon.className = 'fas fa-pause';
        button.classList.remove('btn-primary');
        button.classList.add('btn-outline-primary');
    }
}

function showTaskDelegationModal() {
    const modal = new bootstrap.Modal(document.getElementById('taskDelegationModal'));
    modal.show();
}

function showCollaborationModal() {
    const modal = new bootstrap.Modal(document.getElementById('collaborationModal'));
    modal.show();
}

async function delegateTask() {
    const form = document.getElementById('task-delegation-form');
    const button = event.target;
    const spinner = button.querySelector('.loading-spinner');
    
    // Show loading
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        const formData = new FormData(form);
        const requestData = {
            requester_id: document.getElementById('requester-agent').value,
            task_type: document.getElementById('task-type').value,
            description: document.getElementById('task-description').value,
            task_data: JSON.parse(document.getElementById('task-data').value || '{}'),
            required_capabilities: document.getElementById('required-capabilities').value
                .split(',').map(s => s.trim()).filter(s => s)
        };
        
        const response = await fetch('/api/a2a/tasks/delegate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            dashboard.addMessageToLog(`Task delegated: ${requestData.task_type}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('taskDelegationModal')).hide();
            form.reset();
            dashboard.loadActiveTasks();
        } else {
            throw new Error(result.error || 'Task delegation failed');
        }
        
    } catch (error) {
        dashboard.addMessageToLog(`Task delegation error: ${error.message}`, 'error');
    } finally {
        // Hide loading
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

async function startCollaboration() {
    const form = document.getElementById('collaboration-form');
    const button = event.target;
    const spinner = button.querySelector('.loading-spinner');
    
    // Show loading
    spinner.classList.remove('d-none');
    button.disabled = true;
    
    try {
        const selectedParticipants = Array.from(
            document.querySelectorAll('#participant-checkboxes input:checked')
        ).map(cb => cb.value);
        
        const requestData = {
            coordinator_id: document.getElementById('coordinator-agent').value,
            title: document.getElementById('collab-title').value,
            description: document.getElementById('collab-description').value,
            participant_ids: selectedParticipants,
            required_capabilities: document.getElementById('collab-capabilities').value
                .split(',').map(s => s.trim()).filter(s => s)
        };
        
        const response = await fetch('/api/a2a/collaborations/initiate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            dashboard.addMessageToLog(`Collaboration started: ${requestData.title}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('collaborationModal')).hide();
            form.reset();
            dashboard.loadActiveCollaborations();
        } else {
            throw new Error(result.error || 'Collaboration initiation failed');
        }
        
    } catch (error) {
        dashboard.addMessageToLog(`Collaboration error: ${error.message}`, 'error');
    } finally {
        // Hide loading
        spinner.classList.add('d-none');
        button.disabled = false;
    }
}

// =============================================================================
// TRACE VIEWER FUNCTIONALITY
// =============================================================================

// Global variables for trace viewer
let currentTraces = [];
let selectedTrace = null;
let traceFilters = {
    agent_id: null,
    message_type: null,
    time_range_hours: null
};

// Initialize trace viewer when the tab is shown
document.addEventListener('DOMContentLoaded', function() {
    // Listen for tab changes
    const tracesTab = document.getElementById('traces-tab');
    if (tracesTab) {
        tracesTab.addEventListener('shown.bs.tab', function (e) {
            initializeTraceViewer();
        });
    }
});

async function initializeTraceViewer() {
    try {
        await loadTraceAgents();
        await loadTraces();
        await loadTraceStats();
    } catch (error) {
        console.error('Error initializing trace viewer:', error);
        showTraceError('Failed to initialize trace viewer: ' + error.message);
    }
}

async function loadTraceAgents() {
    try {
        // Populate agent filter dropdown with available agents
        const agentSelect = document.getElementById('trace-agent-filter');
        if (!agentSelect) return;
        
        // Clear existing options (except "All Agents")
        agentSelect.innerHTML = '<option value="">All Agents</option>';
        
        // Get agents from the main dashboard data
        if (dashboard && dashboard.agents) {
            dashboard.agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = agent.name;
                agentSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading trace agents:', error);
    }
}

async function loadTraces() {
    try {
        const tracesList = document.getElementById('traces-list');
        if (!tracesList) return;
        
        // Show loading state
        tracesList.innerHTML = `
            <div class="text-center py-4">
                <div class="loading-spinner mb-2"></div>
                <p class="text-muted">Loading traces...</p>
            </div>
        `;
        
        // Build query parameters
        const params = new URLSearchParams({
            limit: 50,  // Load last 50 traces
            offset: 0
        });
        
        if (traceFilters.agent_id) {
            params.append('agent_id', traceFilters.agent_id);
        }
        if (traceFilters.message_type) {
            params.append('message_type', traceFilters.message_type);
        }
        if (traceFilters.time_range_hours) {
            params.append('time_range_hours', traceFilters.time_range_hours);
        }
        
        const response = await fetch(`/api/a2a/traces/?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load traces');
        }
        
        currentTraces = data.traces || [];
        renderTracesList(currentTraces);
        
    } catch (error) {
        console.error('Error loading traces:', error);
        showTraceError('Failed to load traces: ' + error.message);
    }
}

function renderTracesList(traces) {
    const tracesList = document.getElementById('traces-list');
    if (!tracesList) return;
    
    if (traces.length === 0) {
        tracesList.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No traces found</p>
                <small>Try adjusting your filters or check if tracing is enabled</small>
            </div>
        `;
        return;
    }
    
    const tracesHtml = traces.map(trace => {
        const firstEvent = new Date(trace.first_event);
        const lastEvent = new Date(trace.last_event);
        const duration = lastEvent - firstEvent;
        
        // Determine status based on event patterns
        let status = 'in_progress';
        let statusClass = 'trace-status-in_progress';
        
        if (trace.message_types.some(type => type.includes('failed'))) {
            status = 'failed';
            statusClass = 'trace-status-failed';
        } else if (trace.message_types.some(type => type.includes('delivered') || type.includes('acknowledged'))) {
            status = 'delivered';
            statusClass = 'trace-status-delivered';
        } else if (duration > 300000) { // 5 minutes
            status = 'timeout';
            statusClass = 'trace-status-timeout';
        }
        
        return `
            <div class="trace-list-item" onclick="selectTrace('${trace.trace_id}')" data-trace-id="${trace.trace_id}">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <code class="text-primary">${trace.trace_id.substring(0, 8)}...</code>
                        </h6>
                        <small class="text-muted">
                            ${firstEvent.toLocaleTimeString()} - ${lastEvent.toLocaleTimeString()}
                        </small>
                    </div>
                    <span class="trace-status-badge ${statusClass}">${status}</span>
                </div>
                <div class="trace-summary">
                    <small class="text-muted d-block">
                        <i class="fas fa-exchange-alt"></i> ${trace.event_count} events
                        <i class="fas fa-clock ms-2"></i> ${duration}ms
                    </small>
                    <small class="text-muted">
                        Types: ${trace.message_types.join(', ').substring(0, 50)}${trace.message_types.join(', ').length > 50 ? '...' : ''}
                    </small>
                </div>
            </div>
        `;
    }).join('');
    
    tracesList.innerHTML = tracesHtml;
}

async function selectTrace(traceId) {
    try {
        // Update visual selection
        document.querySelectorAll('.trace-list-item').forEach(item => {
            item.classList.remove('border-primary');
        });
        document.querySelector(`[data-trace-id="${traceId}"]`).classList.add('border-primary');
        
        // Show loading in details panel
        const traceDetails = document.getElementById('trace-details');
        if (!traceDetails) return;
        
        traceDetails.innerHTML = `
            <div class="text-center py-4">
                <div class="loading-spinner mb-2"></div>
                <p class="text-muted">Loading trace details...</p>
            </div>
        `;
        
        // Enable export buttons
        document.getElementById('export-trace-btn').disabled = false;
        document.getElementById('copy-trace-id-btn').disabled = false;
        
        const response = await fetch(`/api/a2a/traces/${traceId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load trace details');
        }
        
        selectedTrace = data.trace;
        renderTraceTimeline(selectedTrace);
        
    } catch (error) {
        console.error('Error loading trace details:', error);
        showTraceDetailsError('Failed to load trace details: ' + error.message);
    }
}

function renderTraceTimeline(trace) {
    const traceDetails = document.getElementById('trace-details');
    if (!traceDetails) return;
    
    const events = trace.events || [];
    
    if (events.length === 0) {
        traceDetails.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                <p>No events found in this trace</p>
            </div>
        `;
        return;
    }
    
    // Sort events by timestamp
    events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    const summary = trace.summary || {};
    
    // Generate trace header
    const headerHtml = `
        <div class="trace-header mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Trace: <code>${trace.trace_id}</code></h6>
                <small class="text-muted">${events.length} events</small>
            </div>
            <div class="row text-center">
                <div class="col-3">
                    <small class="text-muted">Duration</small>
                    <div class="fw-bold text-info">${summary.duration_ms || 0}ms</div>
                </div>
                <div class="col-3">
                    <small class="text-muted">Hops</small>
                    <div class="fw-bold text-primary">${summary.hop_count || 0}</div>
                </div>
                <div class="col-3">
                    <small class="text-muted">Retries</small>
                    <div class="fw-bold text-warning">${summary.retry_count || 0}</div>
                </div>
                <div class="col-3">
                    <small class="text-muted">Status</small>
                    <div class="fw-bold text-${getStatusColor(summary.final_status)}">${summary.final_status || 'unknown'}</div>
                </div>
            </div>
        </div>
    `;
    
    // Generate timeline events
    const timelineHtml = events.map((event, index) => {
        const eventTime = new Date(event.timestamp);
        const iconClass = getEventIcon(event.event_type);
        const eventClass = event.event_type.toLowerCase();
        
        return `
            <div class="trace-event">
                <div class="trace-event-icon ${eventClass}">
                    <i class="${iconClass}"></i>
                </div>
                <div class="trace-event-details">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="mb-1">${formatEventType(event.event_type)}</h6>
                            <small class="text-muted">
                                ${eventTime.toLocaleString()}
                                ${event.status_code ? ` • ${event.status_code}` : ''}
                            </small>
                        </div>
                        ${event.message_type ? `<span class="badge bg-secondary">${event.message_type}</span>` : ''}
                    </div>
                    
                    <div class="row mb-2">
                        ${event.sender_id ? `
                            <div class="col-md-6">
                                <small class="text-muted">From:</small>
                                <div class="fw-bold">${event.sender_id}</div>
                            </div>
                        ` : ''}
                        ${event.recipient_id ? `
                            <div class="col-md-6">
                                <small class="text-muted">To:</small>
                                <div class="fw-bold">${event.recipient_id}</div>
                            </div>
                        ` : ''}
                    </div>
                    
                    ${event.agent_path && event.agent_path.length > 0 ? `
                        <div class="mb-2">
                            <small class="text-muted">Path:</small>
                            <div class="fw-bold">${event.agent_path.join(' → ')}</div>
                        </div>
                    ` : ''}
                    
                    ${event.error_message ? `
                        <div class="mb-2">
                            <small class="text-danger">Error:</small>
                            <div class="text-danger">${event.error_message}</div>
                        </div>
                    ` : ''}
                    
                    ${event.payload_preview ? `
                        <div class="mb-2">
                            <small class="text-muted">Payload Preview:</small>
                            <div class="payload-preview">${event.payload_preview}</div>
                        </div>
                    ` : ''}
                    
                    ${Object.keys(event.metadata || {}).length > 0 ? `
                        <div class="mb-2">
                            <small class="text-muted">Metadata:</small>
                            <div class="payload-preview">${JSON.stringify(event.metadata, null, 2)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    traceDetails.innerHTML = headerHtml + `<div class="trace-timeline">${timelineHtml}</div>`;
}

function getEventIcon(eventType) {
    const iconMap = {
        sent: 'fas fa-paper-plane',
        received: 'fas fa-inbox',
        delivered: 'fas fa-check-circle',
        failed: 'fas fa-times-circle',
        retry: 'fas fa-redo',
        routed: 'fas fa-route',
        acknowledged: 'fas fa-thumbs-up',
        timeout: 'fas fa-clock'
    };
    return iconMap[eventType] || 'fas fa-circle';
}

function formatEventType(eventType) {
    return eventType.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function getStatusColor(status) {
    const colorMap = {
        delivered: 'success',
        acknowledged: 'success',
        failed: 'danger',
        timeout: 'warning',
        in_progress: 'info'
    };
    return colorMap[status] || 'secondary';
}

async function loadTraceStats() {
    try {
        const response = await fetch('/api/a2a/traces/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load trace stats');
        }
        
        const stats = data.stats || {};
        const storage = stats.storage || {};
        
        // Update statistics display
        document.getElementById('total-traces').textContent = storage.unique_traces || 0;
        document.getElementById('successful-traces').textContent = 
            (storage.events_by_type && storage.events_by_type.delivered) || 0;
        document.getElementById('failed-traces').textContent = 
            (storage.events_by_type && storage.events_by_type.failed) || 0;
        
        // Calculate average duration (placeholder)
        document.getElementById('avg-duration').textContent = '~250ms';
        
    } catch (error) {
        console.error('Error loading trace stats:', error);
    }
}

function clearTraceFilters() {
    traceFilters = {
        agent_id: null,
        message_type: null,
        time_range_hours: null
    };
    
    // Clear form fields
    document.getElementById('trace-agent-filter').value = '';
    document.getElementById('trace-type-filter').value = '';
    document.getElementById('trace-time-filter').value = '';
    
    // Reload traces
    loadTraces();
}

function updateTraceFilters() {
    traceFilters.agent_id = document.getElementById('trace-agent-filter').value || null;
    traceFilters.message_type = document.getElementById('trace-type-filter').value || null;
    traceFilters.time_range_hours = document.getElementById('trace-time-filter').value || null;
}

async function exportCurrentTrace() {
    if (!selectedTrace) return;
    
    try {
        const response = await fetch(`/api/a2a/traces/${selectedTrace.trace_id}/export`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `trace_${selectedTrace.trace_id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        dashboard.addMessageToLog(`Trace exported: ${selectedTrace.trace_id}`, 'success');
        
    } catch (error) {
        console.error('Error exporting trace:', error);
        dashboard.addMessageToLog(`Export error: ${error.message}`, 'error');
    }
}

function copyTraceId() {
    if (!selectedTrace) return;
    
    navigator.clipboard.writeText(selectedTrace.trace_id).then(() => {
        dashboard.addMessageToLog(`Trace ID copied: ${selectedTrace.trace_id}`, 'success');
    }).catch(error => {
        console.error('Error copying trace ID:', error);
        dashboard.addMessageToLog(`Copy error: ${error.message}`, 'error');
    });
}

function showTraceError(message) {
    const tracesList = document.getElementById('traces-list');
    if (!tracesList) return;
    
    tracesList.innerHTML = `
        <div class="text-center py-4 text-danger">
            <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
            <p>${message}</p>
        </div>
    `;
}

function showTraceDetailsError(message) {
    const traceDetails = document.getElementById('trace-details');
    if (!traceDetails) return;
    
    traceDetails.innerHTML = `
        <div class="text-center py-4 text-danger">
            <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
            <p>${message}</p>
        </div>
    `;
}

// Filter event handlers
document.addEventListener('DOMContentLoaded', function() {
    // Bind filter change events
    ['trace-agent-filter', 'trace-type-filter', 'trace-time-filter'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', updateTraceFilters);
        }
    });
});