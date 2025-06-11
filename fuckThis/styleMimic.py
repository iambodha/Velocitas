import json
import os
import random
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate

# Import prompts from separate file
from prompts import HOW_TO_DESCRIBE_TONE, SIMILAR_PUBLIC_FIGURES_TEMPLATE, TONE_ANALYSIS_TEMPLATE

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

# Define the default model name once
DEFAULT_MODEL = "gpt-4"

def load_emails(sent_emails_file):
    """
    Load emails from the JSON file with proper error handling.
    
    Args:
        sent_emails_file (str): Path to the JSON file containing sent emails.
        
    Returns:
        list: List of email objects or None if an error occurred.
    """
    try:
        with open(sent_emails_file, "r") as file:
            emails = json.load(file)
        return emails
    except FileNotFoundError:
        print(f"Error: File '{sent_emails_file}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: File '{sent_emails_file}' is not valid JSON.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading emails: {e}")
        return None

def get_langchain_response(prompt, model_name=DEFAULT_MODEL):
    """
    Sends a prompt to the OpenAI API using LangChain and returns the response.
    
    Args:
        prompt (str): The input prompt for the model.
        model_name (str): The OpenAI model to use.

    Returns:
        str: The response from the model.
    """
    try:
        # Initialize the ChatOpenAI model
        chat = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        
        # Get the response
        response = chat.predict(prompt)
        return response.strip()
    except Exception as e:
        return f"An error occurred: {e}"

def get_similar_public_figures(emails, model_name=DEFAULT_MODEL):
    """
    Identifies public figures, authors, or writers whose style matches the content of emails.

    Args:
        emails (list): List of email objects.
        model_name (str): The OpenAI model to use.

    Returns:
        str: A comma-separated list of public figures.
    """
    if not emails:
        return "No emails provided for analysis."
        
    try:
        # Combine email content into a single string
        email_examples = "\n".join(email["body"] for email in emails)

        # Create the prompt using the imported template
        prompt = PromptTemplate(
            input_variables=["email_examples"],
            template=SIMILAR_PUBLIC_FIGURES_TEMPLATE,
        )

        # Format the prompt with the email examples
        final_prompt = prompt.format(email_examples=email_examples)

        # Get the response using the common function
        return get_langchain_response(final_prompt, model_name)
    except Exception as e:
        return f"An error occurred: {e}"

def analyze_tone_from_emails(emails, how_to_describe_tone=HOW_TO_DESCRIBE_TONE, model_name=DEFAULT_MODEL):
    """
    Analyzes the tone qualities of the email examples provided.

    Args:
        emails (list): List of email objects.
        how_to_describe_tone (str): Instructions on how to describe tone.
        model_name (str): The OpenAI model to use.

    Returns:
        str: The tone qualities of the examples.
    """
    if not emails:
        return "No emails provided for analysis."
        
    try:
        # Combine email content into a single string
        email_examples = "\n".join(email["body"] for email in emails)

        # Create the prompt using the imported template
        prompt = PromptTemplate(
            input_variables=["how_to_describe_tone", "email_examples"],
            template=TONE_ANALYSIS_TEMPLATE,
        )

        # Format the prompt with the tone description and email examples
        final_prompt = prompt.format(
            how_to_describe_tone=how_to_describe_tone,
            email_examples=email_examples
        )

        # Get the response using the common function
        return get_langchain_response(final_prompt, model_name)
    except Exception as e:
        return f"An error occurred: {e}"

def get_random_emails(emails, count=11):
    """
    Retrieves a specified number of random emails from the list.

    Args:
        emails (list): List of email objects.
        count (int): Number of random emails to retrieve (default is 12).

    Returns:
        list: A list of randomly selected email objects.
    """
    if not emails:
        return []
        
    try:
        # Ensure the count does not exceed the number of available emails
        count = min(count, len(emails))

        # Randomly select the specified number of emails
        return random.sample(emails, count)
    except Exception as e:
        print(f"An error occurred while selecting random emails: {e}")
        return []

def main():
    sent_emails_file = "sent_emails.json"
    
    # Load all emails once
    all_emails = load_emails(sent_emails_file)
    if not all_emails:
        print("Cannot proceed without valid email data.")
        return
    
    # Get random emails for analysis
    print("\nFetching Random Emails for Analysis:")
    random_emails = get_random_emails(all_emails)
    if not random_emails:
        print("Failed to retrieve random emails.")
        return
    
    # Example usage for identifying similar public figures
    print("\nIdentifying Similar Public Figures:")
    similar_public_figures = get_similar_public_figures(random_emails)
    print("Similar Public Figures:")
    print(similar_public_figures)

    # Example usage for tone analysis
    print("\nAnalyzing Tone Qualities from Emails:")
    tone_analysis = analyze_tone_from_emails(random_emails)
    print("Tone Qualities:")
    print(tone_analysis)

if __name__ == "__main__":
    main()