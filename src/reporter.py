import os
import json
import logging
from datetime import datetime
from jinja2 import Template
from src.config import REPORTS_DIR

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Test Execution Report - Run {{ run_id }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.6);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
            line-height: 1.5;
            background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.05) 0%, transparent 40%);
        }

        .container {
            max-width: 1200px;
            margin: 0;
            margin-left: auto;
            margin-right: auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }

        h1 {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(to right, #3b82f6, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .badge {
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .badge-passed {
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-failed {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: var(--shadow);
        }

        .card-title {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card-value {
            font-size: 1.5rem;
            font-weight: 600;
        }

        .test-description-card {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(22, 28, 45, 0.6) 100%);
        }

        .test-description-text {
            font-size: 1.15rem;
            color: var(--text-primary);
            font-style: italic;
        }

        section {
            margin-bottom: 3rem;
        }

        h2 {
            font-size: 1.5rem;
            margin-bottom: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        h2::before {
            content: '';
            display: inline-block;
            width: 4px;
            height: 1.5rem;
            background-color: var(--accent-blue);
            border-radius: 2px;
        }

        /* Timeline step style */
        .timeline {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .step-item {
            display: flex;
            flex-direction: column;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
        }

        .step-item:hover {
            transform: translateX(4px);
            border-color: rgba(59, 130, 246, 0.25);
        }

        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .step-title {
            font-size: 1.05rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .step-num {
            background-color: rgba(255, 255, 255, 0.05);
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid var(--border-color);
        }

        .step-meta {
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        .step-status {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
        }

        .status-passed {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-healed {
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--accent-yellow);
            border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .status-failed {
            background-color: rgba(239, 68, 68, 0.1);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .step-detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.75rem;
            font-size: 0.875rem;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 0.75rem;
            margin-top: 0.25rem;
        }

        .detail-label {
            color: var(--text-secondary);
            font-weight: 500;
        }

        .detail-value {
            font-family: 'JetBrains Mono', monospace;
            word-break: break-all;
        }

        .error-message {
            background-color: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 0.75rem;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-top: 0.75rem;
            white-space: pre-wrap;
        }

        .screenshot-container {
            margin-top: 1rem;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            max-width: 600px;
        }

        .screenshot-img {
            width: 100%;
            display: block;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .screenshot-img:hover {
            transform: scale(1.02);
        }

        /* Healing log styles */
        .healing-event {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(22, 28, 45, 0.6) 100%);
            border: 1px solid rgba(245, 158, 11, 0.25);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        .healing-event-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(245, 158, 11, 0.2);
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
        }

        .healing-event-title {
            color: var(--accent-yellow);
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .healing-confidence {
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--accent-yellow);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }

        .healing-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 768px) {
            .healing-grid {
                grid-template-columns: 1fr;
            }
        }

        .healing-col-title {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .healing-box {
            background-color: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            min-height: 80px;
            word-break: break-all;
        }

        .healing-arrow {
            display: flex;
            align-items: center;
            justify-content: center;
            grid-column: 1 / -1;
            font-size: 1.5rem;
            color: var(--accent-yellow);
            margin: -0.5rem 0;
        }

        .empty-state {
            color: var(--text-secondary);
            font-style: italic;
            text-align: center;
            padding: 2rem;
            border: 1px dashed var(--border-color);
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Test Run Dashboard</h1>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">ID: {{ run_id }} &bull; Ran on {{ timestamp }}</p>
            </div>
            <div>
                {% if status == "PASSED" %}
                <span class="badge badge-passed">Passed</span>
                {% else %}
                <span class="badge badge-failed">Failed</span>
                {% endif %}
            </div>
        </header>

        <div class="grid">
            <div class="card test-description-card">
                <div class="card-title">Test Scenario Description</div>
                <div class="test-description-text">"{{ test_case_text }}"</div>
            </div>
            <div class="card">
                <div class="card-title">Duration</div>
                <div class="card-value">{{ "%.2f"|format(duration) }} seconds</div>
            </div>
            <div class="card">
                <div class="card-title">Steps Executed</div>
                <div class="card-value">{{ steps|length }}</div>
            </div>
            <div class="card">
                <div class="card-title">Self-Healing Events</div>
                <div class="card-value">{{ healing_logs|length }}</div>
            </div>
        </div>

        {% if healing_logs %}
        <section>
            <h2>Self-Healing Locator Activity</h2>
            {% for log in healing_logs %}
            <div class="healing-event">
                <div class="healing-event-header">
                    <div class="healing-event-title">
                        ⚠️ Recovered Broken Selector (Step {{ log.step_index }})
                    </div>
                    <div class="healing-confidence">
                        Confidence: {{ "%.2f"|format(log.confidence * 100) }}%
                    </div>
                </div>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                    <strong>Action Context:</strong> {{ log.step_description }}
                </p>
                <div class="healing-grid">
                    <div>
                        <div class="healing-col-title">Original Broken Target Description</div>
                        <div class="healing-box" style="border-color: rgba(239, 68, 68, 0.25);">
                            {{ log.original_target }}
                        </div>
                    </div>
                    <div>
                        <div class="healing-col-title">Healed Selector (CSS)</div>
                        <div class="healing-box" style="border-color: rgba(16, 185, 129, 0.25);">
                            {{ log.healed_selector }}
                        </div>
                    </div>
                    <div style="grid-column: 1 / -1; margin-top: -0.5rem;">
                        <div class="healing-col-title">Healed Element DOM Features</div>
                        <div class="healing-box" style="font-size: 0.8rem; background-color: rgba(0,0,0,0.3);">
                            {{ log.healed_representation }}
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </section>
        {% endif %}

        <section>
            <h2>Execution Timeline</h2>
            <div class="timeline">
                {% for step in steps %}
                <div class="step-item">
                    <div class="step-header">
                        <div class="step-title">
                            <span class="step-num">{{ loop.index }}</span>
                            <span>{{ step.description }}</span>
                        </div>
                        <div>
                            {% if step.status == "PASSED" %}
                            <span class="step-status status-passed">Passed</span>
                            {% elif step.status == "HEALED" %}
                            <span class="step-status status-healed">Healed & Passed</span>
                            {% else %}
                            <span class="step-status status-failed">Failed</span>
                            {% endif %}
                        </div>
                    </div>

                    <div class="step-detail-grid">
                        <div>
                            <span class="detail-label">Action:</span>
                            <span class="detail-value">{{ step.action }}</span>
                        </div>
                        <div>
                            <span class="detail-label">Target:</span>
                            <span class="detail-value">{{ step.target }}</span>
                        </div>
                        {% if step.value %}
                        <div>
                            <span class="detail-label">Value:</span>
                            <span class="detail-value">{{ step.value }}</span>
                        </div>
                        {% endif %}
                        <div>
                            <span class="detail-label">Duration:</span>
                            <span class="detail-value">{{ "%.2f"|format(step.duration or 0) }}s</span>
                        </div>
                    </div>

                    {% if step.error %}
                    <div class="error-message">{{ step.error }}</div>
                    {% endif %}

                    {% if step.screenshot %}
                    <div class="screenshot-container">
                        <div class="detail-label" style="margin-bottom: 0.5rem;">Failure Screenshot:</div>
                        <img class="screenshot-img" src="/static/screenshots/{{ step.screenshot }}" alt="Failure Screenshot" onclick="window.open(this.src)">
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </section>
    </div>
</body>
</html>
"""

def generate_report(run_data: dict) -> str:
    """
    Renders the HTML report from run data using the HTML template.
    """
    template = Template(HTML_TEMPLATE)
    rendered_html = template.render(**run_data)
    
    # Save to file
    run_id = run_data["run_id"]
    report_filename = f"report_{run_id}.html"
    report_path = REPORTS_DIR / report_filename
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
        
    logger.info(f"Report generated successfully: {report_path}")
    return report_filename
