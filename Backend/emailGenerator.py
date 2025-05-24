import os
import json
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

def generate_extension_email(tone_analysis, assignment_name, original_deadline, reason_for_extension, professor_name, student_name, days_requested=3, model_name="gpt-4"):
    """
    Generates an email requesting a deadline extension based on the provided tone analysis.
    
    Args:
        tone_analysis (str): Analysis of writing tone to match
        assignment_name (str): Name of the assignment requiring extension
        original_deadline (str): Original deadline date
        reason_for_extension (str): Reason for requesting extension
        professor_name (str): Name of the professor
        student_name (str): Name of the student
        days_requested (int): Number of days requested for extension
        model_name (str): The OpenAI model to use
        
    Returns:
        str: Generated email requesting deadline extension
    """
    try:
        # Initialize the ChatOpenAI model
        chat = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        
        # Create the prompt template
        template = """
        You are an AI that specializes in mimicking writing styles. Your task is to generate an email from a student to their professor requesting a deadline extension.
        
        Here's an analysis of the student's writing style that you should match:
        
        {tone_analysis}
        
        Please write an email with the following details:
        - Assignment: {assignment_name}
        - Original deadline: {original_deadline}
        - Requesting an extension of {days_requested} days
        - Reason for extension: {reason_for_extension}
        - Professor's name: {professor_name}
        - Student's name: {student_name}
        
        The email should be formal and respectful, acknowledging the professor's time and consideration. It should clearly state the request, provide a valid reason, and express appreciation. Follow the writing style described in the tone analysis precisely.
        
        Generate the complete email, including subject line, greeting, body, and sign-off.
        """
        
        # Create the prompt
        prompt = PromptTemplate(
            input_variables=["tone_analysis", "assignment_name", "original_deadline", 
                            "days_requested", "reason_for_extension", 
                            "professor_name", "student_name"],
            template=template,
        )
        
        # Format the prompt with the provided information
        final_prompt = prompt.format(
            tone_analysis=tone_analysis,
            assignment_name=assignment_name,
            original_deadline=original_deadline,
            days_requested=days_requested,
            reason_for_extension=reason_for_extension,
            professor_name=professor_name,
            student_name=student_name
        )
        
        # Get the response
        generated_email = chat.predict(final_prompt)
        return generated_email.strip()
    except Exception as e:
        return f"An error occurred: {e}"

def save_email_to_file(email_content, filename="extension_request_email.txt"):
    """
    Saves the generated email to a text file.
    
    Args:
        email_content (str): Content of the email to save
        filename (str): Name of the file to save the email to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filename, "w") as file:
            file.write(email_content)
        print(f"Email saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving email to file: {e}")
        return False

def main():
    # This is the tone analysis provided
    tone_analysis = """Tone Qualities:
1. Pace: The pace is steady and moderate, with each message conveying a distinct request or information without unnecessary haste.
2. Mood: The mood is respectful and earnest, reflecting the sincerity of the writer's intentions.
3. Tone: The tone is polite, professional, and formal, indicating the writer's respect for the recipients.
4. Voice: The voice is direct and confident, showcasing the writer's clear understanding of their goals or needs.
5. Diction: The diction is primarily academic and formal, with precise and specific language used to convey requests or information.
6. Syntax: The syntax is standard and straightforward, favoring clarity and directness in communication.
7. Imagery: Imagery is minimal, as the focus is more on conveying factual information or making requests.
8. Theme: The themes vary by email but generally revolve around academic requests, project collaborations, or competition participation.
9. Point of View: The point of view is first-person, from the perspective of the writer making requests or providing information.
10. Structure: The structure is formal and organized, often beginning with a greeting, followed by body text, and ending with a closing and signature.
11. Dialogue: There is no dialogue as these are one-way communications, but they do reference past or future discussions.
12. Characterization: Characterization is minimal but the writer comes across as respectful, earnest, and proactive.
13. Setting: The setting is primarily academic or professional environments, as implied by the content of the emails.
14. Foreshadowing, Irony, Symbolism, Allusion, Conflict, Suspense, Climax, Resolution: These aspects are not applicable as the writing examples are formal emails, not a narrative or story."""
    
    
    """Tone Qualities:
1. Pace: The pace of the writing is moderate, with the author taking time to explain their points clearly in each communication.
2. Mood: The mood is businesslike and polite, as the author is writing in a professional context and is asking for assistance or providing information.
3. Tone: The tone is respectful and earnest. The author is serious about their requests or the information they are providing.
4. Voice: The voice is formal and polite, but also proactive and assertive, as the author is clear about what they want or need.
5. Diction: The choice of words is professional, appropriate for the context of each communication. The author uses precise language and technical terminology where necessary.
6. Syntax: The sentences are well-formed and grammatically correct. They are generally complex, with multiple clauses, but they are clear and easy to understand.
7. Imagery: There is little use of imagery in these examples, as the author is writing in a business or academic context and is focused on conveying information rather than creating a vivid picture.
8. Theme: The theme of each piece varies according to the subject matter, but all of them involve the author making a request or providing information in a professional or academic context.
9. Point of View: The point of view is first person, as the author is writing about their own experiences or needs.
10. Structure: The structure of each piece is logical and clear, with the author introducing their topic, explaining their request or the information they are providing, and then concluding politely.
11. Dialogue: There is little dialogue in these examples, as the author is generally writing to one person or a group of people rather than having a conversation.
12. Characterization: The author presents themselves as polite, respectful, proactive, and assertive.
13. Setting: The setting varies according to the subject of each piece, but all of them are set in a professional or academic context.
14. Foreshadowing: There is little use of foreshadowing in these examples, as the author is focused on the present rather than hinting at future events.
15. Irony: There is no use of irony in these examples.
16. Symbolism: There is no use of symbolism in these examples.
17. Allusion: There are no allusions in these examples.
18. Conflict: There is no overt conflict in these examples, although the author is often asking for assistance with a problem or issue.
19. Suspense: There is no suspense in these examples, as the author's aim is to be clear and direct rather than to create tension or uncertainty.
20. Climax: There is no climax in these examples, as they are not narrative pieces.
21. Resolution: Each piece ends with a polite sign-off, but there is no narrative resolution as such."""
    
    # Request user input for the email details
    print("Please provide the following information for your extension request email:")
    assignment_name = input("Assignment name: ")
    original_deadline = input("Original deadline (e.g., May 20, 2025): ")
    reason_for_extension = input("Reason for extension: ")
    professor_name = input("Professor's name: ")
    student_name = input("Your name: ")
    days_requested_input = input("Number of days requested for extension (default is 3): ")
    
    # Set default value if user doesn't provide input
    days_requested = 3
    if days_requested_input:
        try:
            days_requested = int(days_requested_input)
        except ValueError:
            print("Invalid input for days requested. Using default value of 3 days.")
    
    print("\nGenerating email...\n")
    
    # Generate the email
    email_content = generate_extension_email(
        tone_analysis=tone_analysis,
        assignment_name=assignment_name,
        original_deadline=original_deadline,
        reason_for_extension=reason_for_extension,
        professor_name=professor_name,
        student_name=student_name,
        days_requested=days_requested
    )
    
    # Print the generated email
    print("============= GENERATED EMAIL =============")
    print(email_content)
    print("==========================================")
    
    # Ask if the user wants to save the email to a file
    save_option = input("\nDo you want to save this email to a file? (y/n): ")
    if save_option.lower() == 'y':
        save_email_to_file(email_content)

if __name__ == "__main__":
    main()
