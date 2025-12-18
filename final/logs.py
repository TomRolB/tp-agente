"""Logging utilities for multi-agent system."""

from colorama import Fore, Style


def log_orchestrator(message: str):
    print(f"{Fore.CYAN}🎯 [ORCHESTRATOR]{Style.RESET_ALL} {message}")


def log_question_creator(message: str):
    print(f"{Fore.GREEN}✨ [QUESTION CREATOR]{Style.RESET_ALL} {message}")


def log_difficulty_reviewer(message: str):
    print(f"{Fore.YELLOW}⚖️  [DIFFICULTY REVIEWER]{Style.RESET_ALL} {message}")


def log_feedback_agent(message: str):
    print(f"{Fore.MAGENTA}💡 [FEEDBACK AGENT]{Style.RESET_ALL} {message}")


def log_user_input(message: str):
    print(f"{Fore.BLUE}👤 [USER INPUT]{Style.RESET_ALL} {message}")


def log_user_output(message: str):
    print(f"{Fore.WHITE}{Style.BRIGHT}📢 [SYSTEM → USER]{Style.RESET_ALL} {message}")


def log_separator():
    print(f"{Fore.LIGHTBLACK_EX}{'=' * 80}{Style.RESET_ALL}")


def log_open_question_creator(message: str):
    """Log messages from Open-Ended Question Creator (reuses question_creator style)"""
    print(f"{Fore.GREEN}✨ [OPEN QUESTION CREATOR]{Style.RESET_ALL} {message}")


def log_answer_evaluator(message: str):
    """Log messages from Open-Ended Answer Evaluator"""
    print(f"{Fore.BLUE}📝 [ANSWER EVALUATOR]{Style.RESET_ALL} {message}")
