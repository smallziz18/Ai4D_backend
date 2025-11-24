"""
Package des agents IA.
"""
from src.ai_agents.agents.profiler_agent import profiler_agent
from src.ai_agents.agents.question_generator_agent import question_generator_agent
from src.ai_agents.agents.evaluator_agent import evaluator_agent
from src.ai_agents.agents.tutoring_agent import tutoring_agent
from src.ai_agents.agents.recommendation_agent import recommendation_agent
from src.ai_agents.agents.planning_agent import planning_agent
from src.ai_agents.agents.progression_agent import progression_agent
from src.ai_agents.agents.visualization_agent import visualization_agent
from src.ai_agents.agents.content_generation_agent import content_generation_agent

__all__ = [
    "profiler_agent",
    "question_generator_agent",
    "evaluator_agent",
    "tutoring_agent",
    "recommendation_agent",
    "planning_agent",
    "progression_agent",
    "visualization_agent",
    "content_generation_agent"
]
