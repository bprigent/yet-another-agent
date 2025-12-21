"""Main entry point for the Deep Agent."""

import os
from dotenv import load_dotenv
from deepagents import create_deep_agent
from tools.internet_search import internet_search

# Load environment variables
load_dotenv()


def main():
    """Create and run the Deep Agent."""
    
    # Verify API keys are set
    google_api_key = os.getenv("GOOGLE_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable is required")
    
    # Set the API key as an environment variable for the agent
    os.environ["GOOGLE_API_KEY"] = google_api_key
    
    # Create the Deep Agent with the search tool
    # Model will default to Gemini if GOOGLE_API_KEY is set
    agent = create_deep_agent(
        tools=[internet_search]
    )
    
    # Run the agent interactively
    print("Deep Agent is ready! Type 'quit' or 'exit' to stop.")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("\nAgent: ", end="", flush=True)
        # Invoke the agent with the user's message
        response = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
        # Extract the response content
        if isinstance(response, dict) and "messages" in response:
            messages = response["messages"]
            if messages and hasattr(messages[-1], "content"):
                print(messages[-1].content)
            else:
                print(response)
        else:
            print(response)


if __name__ == "__main__":
    main()

