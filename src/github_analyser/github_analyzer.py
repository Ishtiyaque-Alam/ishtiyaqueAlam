import requests, zipfile, io, os
from ..pipeline.analyzer import CodeAnalyzer
def download_github_repo(owner, repo, dest_folder="/tmp/repo"):
    url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    z.extractall(dest_folder)
    print(f"Repo extracted to {dest_folder}")

if __name__=="__main__":
    print("Enter the name of the GitHub repository (format: owner/repo): ")
    repo_input = input().strip()
    if '/' not in repo_input:
        print("Invalid format. Please use 'owner/repo'.")
    else:
        owner, repo = repo_input.split('/')
        download_github_repo(owner, repo,dest_folder="./downloaded_repo")
        analyzer=CodeAnalyzer(output_dir="./analysis_output")
        summary=analyzer.analyze("./downloaded_repo")
        print('Analysis is successfull Do you want to chat with the bot ? (y/n)')
        ans=input().strip().lower()
        if ans=='y':
            from src.qa_agent.conv_bot import ConversationalBot
            from src.qa_agent.manage_chunks import TopicSwitchingRetriever
            from src.qa_agent.debugger_agent import LLMClient, DebuggerAgent, Planner, DebugMain
            llm = LLMClient()
            planner = Planner(llm)
            topic_retriever = TopicSwitchingRetriever()
            analyzer = DebugMain(llm)
            debugger_agent = DebuggerAgent(planner, topic_retriever, analyzer)
            bot = ConversationalBot(topic_retriever, debugger_agent, llm)

            print("ConversationalBot CLI. Type 'exit' to quit.")
            while True:
                try:
                    user_query = input("You: ").strip()
                    if user_query.lower() in ("exit", "quit"): break
                    response = bot.handle_query(user_query)
                    print(f"Bot: {response}\n")
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting chat.")