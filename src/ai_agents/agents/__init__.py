"""
Package des agents IA.
"""

# Imports relatifs des instances d'agents disponibles dans ce package
from .profiler_agent import profiler_agent
from .question_generator_agent import question_generator_agent
from .evaluator_agent import evaluator_agent
from .chatbot_agent import chatbot_agent
from .course_manager_agent import course_manager_agent
from .tutoring_agent import tutoring_agent
from .course_recommendation_agent import course_recommendation_agent
from .planning_agent import planning_agent
from .progression_agent import progression_agent
from .visualization_agent import visualization_agent
from .content_generation_agent import content_generation_agent
from .recommendation_agent import recommendation_agent

__all__ = [
    "profiler_agent",
    "question_generator_agent",
    "evaluator_agent",
    "chatbot_agent",
    "course_manager_agent",
    "tutoring_agent",
    "course_recommendation_agent",
    "planning_agent",
    "progression_agent",
    "visualization_agent",
    "content_generation_agent",
    "recommendation_agent",
]
