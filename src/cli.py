import argparse
from src.pipeline.analyzer import CodeAnalyzer
from src.qa_agent.conv_bot import ConversationalBot
from src.qa_agent.manage_chunks import TopicSwitchingRetriever
from src.vector_db.chroma_manager import ChromaManager
from src.qa_agent.debugger_agent import LLMClient, DebuggerAgent, Planner, DebugMain
from src.github_analyser.github_analyzer import download_github_repo
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.panel import Panel
import time

def typing_animation(text, delay=0.005):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def main():
    parser = argparse.ArgumentParser(prog="cq-agent", description="CQ Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a local codebase")
    analyze_parser.add_argument("path", help="Path to codebase")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat with the QA bot")

    # GitHub command
    github_parser = subparsers.add_parser("github", help="Analyze a GitHub repo")
    github_parser.add_argument("repo", help="GitHub repo in owner/repo format")

    args = parser.parse_args()

    # Initialize components
    llm = LLMClient()
    planner = Planner(llm)
    chroma_manager = ChromaManager()
    topic_retriever = TopicSwitchingRetriever(chroma_manager)
    analyzer = DebugMain(llm)
    debugger_agent = DebuggerAgent(planner, chroma_manager, analyzer)
    bot = ConversationalBot(topic_retriever, debugger_agent, llm)

    if args.command == "analyze":
        console = Console()
        with Live(Spinner("dots", text="Analyzing..."), refresh_per_second=10, console=console):
            code_analyzer = CodeAnalyzer(output_dir="./analysis_output")
            summary = code_analyzer.analyze(args.path)
        console.print("[bold green]Analysis Complete![/bold green]")
        print(summary)

    elif args.command == "chat":
        console = Console()
        console.print("[bold green]CQ Agent Chat. Type 'exit' to quit.[/bold green]")
        while True:
            user_query = console.input("[bold blue]You:[/bold blue] ")
            if user_query.lower() in ["exit", "quit"]:
                break
            with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10, console=console):
                response = bot.handle_query(user_query)
            console.print(Panel.fit(response, title="Bot", border_style="magenta"))
            typing_animation(response)

    elif args.command == "github":
        console = Console()
        with Live(Spinner("dots", text="Downloading and Analyzing GitHub repo..."), refresh_per_second=10, console=console):
            owner, repo = args.repo.split("/")
            download_github_repo(owner, repo, dest_folder="./downloaded_repo")
            code_analyzer = CodeAnalyzer(output_dir="./analysis_output")
            summary = code_analyzer.analyze("./downloaded_repo")
        console.print("[bold green]GitHub Analysis Complete![/bold green]")
        print(summary)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
    